#!/usr/bin/env python3
"""PreToolUse hook: stop tool calls that reach for secret-bearing files.

What this is: a guardrail against *accidental* secret reads -- Claude running
`cat .env`, `grep -r KEY .`, or `Read .env` because it was trying to debug a
config problem. What this is NOT: a sandbox. A determined process can always
build the filename at runtime (base64, chr(), environment tricks) and no
string inspection will see it. The real protection for a secret is that it
never needs to enter the conversation; this hook just makes the obvious paths
fail loudly with instructions for the right path.

Why a hook at all: permission deny rules only match the exact spellings you
list, while any usable allow list hands out a dozen other ways to print a file
(`head`, `grep`, `python -c`, ...). A PreToolUse hook that exits 2 stops the
call before permission rules are evaluated, so it beats allow rules too.

Surfaces checked:
  Bash / PowerShell   the command string (case-insensitive, quote- and
                      escape-normalised, glob-aware, recursive-search-aware)
  Read / Edit / Write / MultiEdit / NotebookEdit   the target file path
  Grep / Glob         the search path and glob/pattern arguments

Always allowed: .env.example, .env.sample, .env.template (committed, names only).

Exit codes:
  0  allow
  2  block, with the reason on stderr for Claude to read
  Any internal error, unparseable payload or unexpected shape also exits 2:
  this hook fails CLOSED. (Claude Code treats other non-zero codes as
  "non-blocking", i.e. it would let the call through.)
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys

SAFE_ENV_NAMES = {".env.example", ".env.sample", ".env.template"}

# Concrete names used for glob matching (does `.e*` / `.en?` / `.[e]nv` hit one?).
GLOB_PROBE_NAMES = [".env", ".env.local", ".env.production", ".env.development"]

# Literal filename patterns, matched against several normalised spellings of the
# command. `(?<![\w.\-])` keeps `process.env`, `os.environ`, `foo.env` and
# `.venv` from matching; `(?![\w\-])` keeps `.environment` / `.envrc` out.
_ENV_RE = re.compile(r"(?<![\w.\-])\.env((?:\.[\w\-]+)*)(?![\w\-])")
_OTHER_SECRET_RES = [
    re.compile(r"(?<![\w\-])secrets\.json\b"),
    re.compile(r"(?<![\w\-])appsettings\.local\.json\b"),
    re.compile(r"(?<![\w\-])local\.settings\.json\b"),
    re.compile(r"\.(?:pem|pfx|p12)(?![\w])"),
]

# Recursive content search over a directory reads .env without naming it.
_READERS = (
    r"(?:cat|head|tail|less|more|grep|egrep|fgrep|rg|sed|awk|strings|xxd|od|"
    r"base64|nl|tac|cp|tar|zip|python\d*(?:\.\d+)?|py|node|ruby|perl|type|"
    r"get-content|gc|select-string|sls)"
)
_RECURSIVE_SEARCH_RES = [
    re.compile(r"\bfindstr\b[^|;&\n]*?\s/s(?=\s|$)"),
    # find ... -exec cat {}  /  find ... | xargs grep
    re.compile(r"\bfind\b[^;&\n]*?(?:-exec(?:dir)?|-ok)\s+" + _READERS + r"\b"),
    re.compile(r"\bfind\b[^;&\n]*\|\s*xargs\s+(?:-\S+\s+)*" + _READERS + r"\b"),
]
# PowerShell: Get-ChildItem -Recurse piped into a content reader
_PS_RECURSE_RE = re.compile(r"\b(?:get-childitem|gci|dir|ls)\b[^;\n]*?\s-(?:recurse|rec\w*|r)(?=\s|$)")
_PS_READ_RE = re.compile(r"\b(?:select-string|sls|get-content|gc|cat|type)\b")

FILE_TOOLS = {"Read", "Edit", "Write", "MultiEdit", "NotebookEdit"}
SEARCH_TOOLS = {"Grep", "Glob"}
SHELL_TOOLS = {"Bash", "PowerShell"}

# ASCII only: on Windows, stderr is encoded with the console code page, and a
# non-ASCII character here arrives in Claude's transcript as mojibake.
DENIAL = """Blocked by .claude/hooks/block_secret_access.py: {reason}

This project keeps secrets in a gitignored .env that you (Claude) do not read.
This hook is a guardrail against accidental reads, not a sandbox -- do not try
to work around it; ask the developer instead. What to do:
  - See WHICH keys are set (names only, never values):
      Windows:      powershell -NoProfile -ExecutionPolicy Bypass -File scripts/secure/Test-Readiness.ps1
      macOS/Linux:  pwsh -File scripts/secure/Test-Readiness.ps1   (if PowerShell 7 is installed)
  - Get a key filled in: ask the developer to run scripts/secure/Set-ProjectSecrets.ps1
    in their own terminal. You cannot run it -- your stdin is the null device.
  - .env.example / .env.sample / .env.template are committed and safe to read.
  - Searching code? Use the Grep tool, or pass explicit source paths to grep
    instead of a recursive search over the project root."""


def _variants(command: str) -> list[str]:
    """Spellings of the command a secret name could hide behind."""
    low = command.lower()
    slashed = low.replace("\\", "/")                      # ..\proj\.env  -> ../proj/.env
    unescaped = low.replace("\\", "")                     # .e\nv         -> .env
    out = []
    for base in (slashed, unescaped):
        adjacent = re.sub(r"\b[rbuf]{1,2}(?=[\"'])", "", base)       # r'.env'    -> '.env'
        adjacent = re.sub(r"([\"'])\s+([\"'])", r"\1\2", adjacent)   # '.e' 'nv' -> '.e''nv'
        unquoted = re.sub(r"[\"'`]", "", adjacent)        # '.e''nv'      -> .env
        joined = re.sub(r"\s*\+\s*", "", unquoted)        # '.'+'env'     -> .env
        out.extend([base, unquoted, joined])
    return list(dict.fromkeys(out))


def _env_hit(text: str) -> bool:
    for m in _ENV_RE.finditer(text):
        if m.group(0) not in SAFE_ENV_NAMES:
            return True
    return False


def _glob_hit(text: str) -> bool:
    """Does any glob-bearing path component expand to a dotenv file?"""
    for token in re.split(r"[\s;|&<>(){}=,:/]+", text):
        if not token or not any(ch in token for ch in "*?["):
            continue
        # Pure wildcards (`*`, `*.*`, `**`) don't match dotfiles in POSIX shells;
        # blocking them would block `ls *` and friends.
        if not token.startswith(".") and not re.search(r"[a-z0-9]", token):
            continue
        for name in GLOB_PROBE_NAMES:
            if fnmatch.fnmatchcase(name, token):
                return True
    return False


# grep -r / -R / -rn / --recursive
_GREP_RECURSIVE_FLAG = re.compile(r"-[a-zA-Z]*[rR][a-zA-Z]*|--recursive|--dereference-recursive|--directories=recurse")
# ripgrep already skips hidden + gitignored files; these flags turn that off
_RG_UNHIDE_FLAG = re.compile(r"-[a-zA-Z]*u[a-zA-Z]*|--hidden|--no-ignore\S*|--unrestricted|-\.")
# Case-sensitive on purpose: grep's -A/-B/-C take a number, -a/-b/-c take nothing.
_OPTS_WITH_ARG = {"-e", "-f", "-m", "-A", "-B", "-C", "-d", "-D", "-g", "-t", "-T", "--regexp",
                  "--file", "--max-count", "--context", "--glob", "--type", "--include", "--exclude"}
_PATTERN_OPTS = {"-e", "--regexp", "-f", "--file"}
# Search roots that sweep up the project-root .env (or anything else).
_ROOTISH = re.compile(r"\.{1,2}/?|\*|~.*|/.*|[a-zA-Z]:.*|\$.*|\.\./.*|%.*")


def _recursive_grep_over_root(command: str) -> bool:
    """`grep -rn x components/` is fine; `grep -r x .`, `grep -r x` (no path = cwd),
    `grep -r x /abs` or `grep -r x $DIR` would read .env without naming it."""
    for segment in re.split(r"[|;&\n]+", command.replace("\\", "/")):
        tokens = [t.strip("\"'") for t in segment.split()]
        idx = next((i for i, t in enumerate(tokens) if re.fullmatch(r"[ef]?grep|rg", t.lower())), None)
        if idx is None:
            continue
        tool, args = tokens[idx].lower(), tokens[idx + 1:]
        flag_re = _RG_UNHIDE_FLAG if tool == "rg" else _GREP_RECURSIVE_FLAG
        if not any(flag_re.fullmatch(a) for a in args):
            continue
        positional, pattern_given, skip = [], False, False
        for a in args:
            if skip:
                skip = False
            elif a.startswith("-"):
                pattern_given |= a in _PATTERN_OPTS
                skip = a in _OPTS_WITH_ARG
            else:
                positional.append(a)
        paths = positional if pattern_given else positional[1:]
        if not paths or any(_ROOTISH.fullmatch(p) for p in paths):
            return True
    return False


def check_command(command: str) -> str | None:
    variants = _variants(command)
    for text in variants:
        if _env_hit(text):
            return "the command references a .env file"
        if any(r.search(text) for r in _OTHER_SECRET_RES):
            return "the command references a secret-bearing file (secrets.json / *.local.json / key material)"
        if _glob_hit(text):
            return "the command uses a wildcard that expands to a .env file"
    low = variants[0]
    if _recursive_grep_over_root(command):
        return "recursive grep/rg over the project root (or no explicit path) would read .env without naming it"
    if any(r.search(low) for r in _RECURSIVE_SEARCH_RES):
        return "recursive content search over a directory would read .env without naming it"
    if _PS_RECURSE_RE.search(low) and _PS_READ_RE.search(low):
        return "recursive Get-ChildItem piped into a content reader would read .env"
    return None


def _basename(path: str) -> str:
    return re.split(r"[\\/]", path.strip().strip("\"'"))[-1].lower()


def check_path(path: str) -> str | None:
    name = _basename(path)
    if name in SAFE_ENV_NAMES:
        return None
    if re.fullmatch(r"\.env(\..+)?", name):
        return f"{name} is a secrets file"
    if any(r.search(name) for r in _OTHER_SECRET_RES):
        return f"{name} is a secret-bearing file"
    if _glob_hit(name):
        return f"the pattern {name!r} would match a .env file"
    return None


def evaluate(payload: object) -> str | None:
    """Return a block reason, or None to allow."""
    if not isinstance(payload, dict):
        return "the hook payload was not a JSON object (failing closed)"
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {"command": json.dumps(tool_input)} if tool in SHELL_TOOLS else {}

    if tool in SHELL_TOOLS:
        command = tool_input.get("command")
        if not isinstance(command, str):
            command = json.dumps(command)
        return check_command(command)

    if tool in FILE_TOOLS:
        for key in ("file_path", "notebook_path", "path"):
            value = tool_input.get(key)
            if isinstance(value, str) and (reason := check_path(value)):
                return reason
        return None

    if tool in SEARCH_TOOLS:
        for key in ("path", "glob", "pattern"):
            value = tool_input.get(key)
            if not isinstance(value, str):
                continue
            # Grep's `pattern` is a regex over file *contents*, not a filename.
            if tool == "Grep" and key == "pattern":
                continue
            for part in re.split(r"[\s,{}]+", value):
                if part and (reason := check_path(part)):
                    return reason
        return None

    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = None
        reason = evaluate(payload)
    except Exception as exc:  # noqa: BLE001 -- any bug must block, not allow
        reason = f"the hook itself errored ({type(exc).__name__}), failing closed"
    if reason:
        print(DENIAL.format(reason=reason), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

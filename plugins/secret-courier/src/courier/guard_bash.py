"""Bash / PowerShell PreToolUse guard: ``check_bash_command(command) -> reason | None``.

Order of checks (every one is a deny; the only allowlist is the metadata-verb / trusted-script rule, consulted
only for the program a segment actually invokes):

1. a secret-shaped value anywhere in the command (scanner rules);
2. tokens that print or decrypt secret values wherever they appear (``config/guard-policy.json``
   ``value_dump_tokens``: ``ConvertFrom-SecureString``, ``keyring get``, ``process.env``, ``az keyvault secret
   show``, ``aws secretsmanager get-secret-value`` ...), references to credential-named environment variables,
   environment and git-config dumps, and an encoded PowerShell command wherever it sits in the line;
3. per segment (split on ``&& || | ; & newline $( ( ) { } backtick`` outside single quotes, ``#`` comments
   stripped): a nested shell (``bash -c``, ``pwsh -Command``, ``cmd /c``) is checked recursively; a script file
   the segment runs (``pwsh -File x.ps1``, ``python x.py``, ``node x.js``) is scanned with the same rules when it
   exists; bare ``env`` / ``set`` / ``export``; and any path-like token or glob naming a secret-bearing file
   unless the segment's program only reports metadata (``ls``, ``Test-Path``, ``git status`` ...) or is a
   trusted ops script. A metadata producer that names a denied path taints what it feeds through a pipe or a
   command substitution: ``ls .env | xargs cat`` and ``cat $(ls .env)`` are reads.

Honest limit: a path or token assembled inside an interpreter (``'.e'+'nv'``) is invisible to a text check;
the Read/Write hooks and the OS ACL on the store are the floor beneath this one.
"""

from __future__ import annotations

import fnmatch
import os
import re

from courier.guard_paths import canonical_forms, is_denied_path
from courier.policy import POLICY
from courier.scan import scan_text

SECRET_VALUE_MSG = (
    "Blocked: the command contains a secret-shaped value ({rules}). "
    "Store it with `courier prompt <name>` and reference it by name (secret-courier)."
)
_INSTEAD = (
    "Instead: `courier exists <name>` says where a value is held; `courier run --env VAR=<store>:<name> -- <command>` "
    "gives a program the value without printing it (secret-courier)."
)
SECRET_FILE_MSG = "Blocked: that command reads a secret-bearing file, and Claude handles secret NAMES only. " + _INSTEAD
SCRIPT_FILE_MSG = (
    "Blocked: the script that command runs {what}. Claude never runs a script that prints or decrypts secret values. "
    + _INSTEAD
)
EXPOSES_MSG = "Blocked: that command exposes secret values ({what}), and Claude handles secret NAMES only. " + _INSTEAD

_SECRET_NAMES = POLICY.secret_env_names
_DENIED_TOKEN_RE = re.compile(r"(?i)(?<![\w-])(?:" + "|".join(POLICY.value_dump_tokens) + r")(?![\w-])")
_ENV_REF_RE = re.compile(
    rf"(?:\$(?:env:|\{{env:)?\{{?{_SECRET_NAMES}\b|%{_SECRET_NAMES}%|(?i:env:)[\\/]?{_SECRET_NAMES}\b|"
    rf"(?:GetEnvironmentVariable|environ(?:\.get)?|getenv)\s*[(\[]\s*[\"']{_SECRET_NAMES}\b)"
)
_ENV_DUMP_RE = re.compile(
    r"(?i)(?<![\w-])(?:gci|ls|dir|get-childitem|get-item|gi|cat|type|get-content)\s+(?:-\w+\s+)*[\"']?env:|"
    r"\bos\.environ(?:\s*\)|\.(?:items|copy|keys|values)\s*\()"
)
_GIT_CONFIG_DUMP_RE = re.compile(
    r"(?i)\bgit\b[^|;&]*\bconfig\b[^|;&]*(?:--list|-l\b|--get-regexp|--show-origin|--get-urlmatch|--get-all|credential|\burl\b|remote\.)|"
    r"\bgit\b[^|;&]*\bremote\s+(?:-v\b|--verbose|show\b|get-url\b)|\bgit\b[^|;&]*--get-url|\bgit[ -]credential"
)
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_]\w*=")
_PREFIX_WORDS = frozenset({"sudo", "nohup", "time", "exec", "command", "builtin", "start"})
_START_SWITCHES = frozenset({"/b", "/wait", "/min", "/max"})
_RAW_TOKEN_RE = re.compile(r"\"[^\"]*\"|'[^']*'|\S+")
_CANDIDATE_SPLIT_RE = re.compile(r"[\s=@<>,;()\[\]{}|&\"'`]+")
_SAFE_PROGRAMS = frozenset(POLICY.metadata_programs)
_SAFE_GIT = frozenset(POLICY.safe_git)
_GIT_VALUE_FLAGS = frozenset({"-c", "-C", "--git-dir", "--work-tree", "--namespace"})
_PWSH = frozenset({"pwsh", "powershell"})
_PWSH_SKIP_FLAGS = frozenset(
    {"-noprofile", "-nologo", "-noninteractive", "-sta", "-mta", "-file", "-f", "-command", "-c", "-noexit"}
)
_PWSH_VALUE_FLAGS = frozenset({"-executionpolicy", "-ep", "-ex", "-workingdirectory", "-wd", "-version", "-v"})
_TRUSTED_SCRIPT_RE = (
    re.compile(r"(?:^|/)(?:" + "|".join(re.escape(d) for d in POLICY.trusted_script_dirs) + r")/[\w.-]+\.ps1$")
    if POLICY.trusted_script_dirs
    else re.compile(r"(?!)")
)
_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
_INTERPRETERS = frozenset(POLICY.interpreters) - _PWSH - _SHELLS - {"cmd"}
_SCRIPT_SUFFIXES = (
    ".ps1",
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".rb",
    ".pl",
    ".php",
    ".sh",
    ".bash",
    ".zsh",
    ".cmd",
    ".bat",
)
_MAX_SCRIPT_BYTES = 256 * 1024
_MAX_DEPTH = 3
_FLOW_OPS = frozenset({"|", "$(", "`"})


def secret_findings(text: str) -> list[str]:
    return sorted({f.rule for f in scan_text(text or "")})


def split_segments_ops(command: str) -> list[tuple[str, str]]:
    """``(segment, operator before it)`` pairs with ``#`` comments removed."""
    segs: list[tuple[str, str]] = []
    buf: list[str] = []
    op = ""
    quote: str | None = None
    i, n = 0, len(command)

    def flush(next_op: str) -> None:
        nonlocal buf, op
        text = "".join(buf).strip()
        if text:
            segs.append((text, op))
        buf = []
        op = next_op

    while i < n:
        ch = command[i]
        if quote == "'":
            if ch == "'":
                quote = None
            buf.append(ch)
            i += 1
        elif quote == '"':
            if ch == '"':
                quote = None
                buf.append(ch)
                i += 1
            elif command.startswith("$(", i) or ch == "`":
                flush("$(" if ch == "$" else "`")
                i += 2 if ch == "$" else 1
            else:
                buf.append(ch)
                i += 1
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
        elif ch == "#" and (not buf or buf[-1].isspace()):
            j = command.find("\n", i)
            i = n if j < 0 else j
        elif command.startswith(("&&", "||", "$("), i):
            flush(command[i : i + 2])
            i += 2
        elif ch in "|;\n&(){}`":
            flush(ch)
            i += 1
        else:
            buf.append(ch)
            i += 1
    flush("")
    return segs


def split_segments(command: str) -> list[str]:
    return [seg for seg, _ in split_segments_ops(command)]


def _unquote(tok: str) -> str:
    return tok[1:-1] if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'" else tok


def _program(segment: str) -> tuple[str, list[str]]:
    toks = [_unquote(t) for t in _RAW_TOKEN_RE.findall(segment)]
    i = 0
    while i < len(toks):
        low = toks[i].lower()
        wrapper = low == "env" and any(not t.startswith("-") for t in toks[i + 1 :])
        if low == "start":
            i += 1
            while i < len(toks) and toks[i].lower() in _START_SWITCHES:
                i += 1
            continue
        if not (_ENV_ASSIGN_RE.match(toks[i]) or low in _PREFIX_WORDS or wrapper):
            break
        i += 1
    if i >= len(toks):
        return "", []
    return toks[i], toks[i + 1 :]


def _prog_name(token: str) -> str:
    name = os.path.basename(token.replace("\\", "/")).lower().lstrip("&")
    return re.sub(r"\.(?:exe|cmd|bat)$", "", name)


def _git_subcommand(args: list[str]) -> str:
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a.startswith("-"):
            skip = a in _GIT_VALUE_FLAGS
            continue
        return a.lower()
    return ""


def _pwsh_script(args: list[str]) -> str:
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        low = a.lower()
        if low in _PWSH_SKIP_FLAGS:
            continue
        if low in _PWSH_VALUE_FLAGS:
            skip = True
            continue
        if low.startswith("-"):
            continue
        return a.lstrip("& ")
    return ""


def _is_trusted_script(token: str) -> bool:
    return any(_TRUSTED_SCRIPT_RE.search(f) for f in canonical_forms(token))


def _metadata_only(segment: str) -> bool:
    prog, args = _program(segment)
    if not prog:
        return False
    name = _prog_name(prog)
    if name in _SAFE_PROGRAMS:
        return True
    if name == "git":
        return _git_subcommand(args) in _SAFE_GIT
    if name in _PWSH:
        return _is_trusted_script(_pwsh_script(args))
    return _is_trusted_script(prog)


def _path_candidates(segment: str) -> list[str]:
    out: list[str] = []
    for c in _CANDIDATE_SPLIT_RE.split(segment):
        if not c:
            continue
        out.append(c)
        head, sep, tail = c.partition(":")
        if sep and tail and len(head) != 1:
            out.append(tail)
    return out


def _touches_denied_path(segment: str) -> bool:
    return any(is_denied_path(c) for c in _path_candidates(segment))


def _glob_components(token: str) -> list[str]:
    p = token.strip().strip("\"'").replace("\\", "/")
    if p.startswith("~"):
        p = os.path.expanduser("~").replace("\\", "/") + p[1:]
    return [c.lower() for c in p.split("/") if c and c != "."]


def _glob_touches_denied(segment: str) -> bool:
    """A wildcard token that could select a denied file (``denied_samples``) or walk a denied directory; a
    wildcard-only last component (``build/*``) selects nothing by name."""
    samples = [s.lower().split("/") for s in POLICY.denied_samples]
    dirs = [d.lower().split("/") for d in POLICY.denied_dirs]
    for tok in _path_candidates(segment):
        if not any(ch in tok for ch in "*?") or tok.startswith("-") or "://" in tok:
            continue
        comps = _glob_components(tok)
        if not comps:
            continue
        literal = [bool(re.search(r"[^*?.]", c)) for c in comps]
        for d in dirs:
            k = len(d)
            for i in range(len(comps) - k + 1):
                window = comps[i : i + k]
                if any(literal[i : i + k]) and all(fnmatch.fnmatchcase(d[j], window[j]) for j in range(k)):
                    return True
        if not re.search(r"[^*?.]", comps[-1]):
            continue
        for s in samples:
            k = min(len(s), len(comps))
            if all(fnmatch.fnmatchcase(s[-k + j], comps[-k + j]) for j in range(k)):
                return True
    return False


def _encoded_reason(command: str) -> str | None:
    toks = [_unquote(t) for t in _RAW_TOKEN_RE.findall(command)]
    for i, tok in enumerate(toks):
        if _prog_name(tok) not in _PWSH:
            continue
        for follow in toks[i + 1 : i + 9]:
            if follow[:1] not in "-/":
                continue
            flag = follow[1:].lower()
            if flag in {"e", "ec"} or (len(flag) >= 2 and "encodedcommand".startswith(flag)):
                return EXPOSES_MSG.format(what="an encoded PowerShell command hides the command from the guard")
    return None


def _dump_reason(segment: str) -> str | None:
    prog, args = _program(segment)
    name = _prog_name(prog) if prog else ""
    if name in {"env", "set", "export"} and not args:
        return EXPOSES_MSG.format(what=f"{name} dumps the environment")
    return None


def _inner_command(segment: str) -> str | None:
    prog, args = _program(segment)
    if not prog:
        return None
    name = _prog_name(prog)
    if name in _SHELLS:
        for i, a in enumerate(args):
            if a == "-c" and i + 1 < len(args):
                return args[i + 1]
        return None
    if name in _PWSH:
        for i, a in enumerate(args):
            if a.lower() in {"-command", "-c"}:
                return " ".join(args[i + 1 :]) or None
        return None
    if name == "cmd":
        for i, a in enumerate(args):
            if a.lower() in {"/c", "/k"}:
                return " ".join(args[i + 1 :]) or None
    return None


def _script_arg(segment: str) -> str | None:
    prog, args = _program(segment)
    if not prog:
        return None
    name = _prog_name(prog)
    if name in _PWSH:
        if any(a.lower() in {"-command", "-c"} for a in args):
            return None
        cand = _pwsh_script(args)
    elif name in _SHELLS or name in _INTERPRETERS:
        cand = ""
        for a in args:
            if a in {"-m", "-c", "-e", "-r"}:
                return None
            if a.startswith("-") or a.lower() in {"run", "eval"}:
                continue
            cand = a
            break
    else:
        return None
    return cand if cand and cand.lower().endswith(_SCRIPT_SUFFIXES) else None


def _text_reason(text: str) -> str | None:
    rules = secret_findings(text)
    if rules:
        return f"contains a secret-shaped value ({', '.join(rules)})"
    if _DENIED_TOKEN_RE.search(text) or _ENV_REF_RE.search(text):
        return "contains a secret-reading token or credential variable"
    if _ENV_DUMP_RE.search(text) or _GIT_CONFIG_DUMP_RE.search(text) or _encoded_reason(text):
        return "dumps the environment, git config or an encoded command"
    for line in text.splitlines():
        if _dump_reason(line) or _touches_denied_path(line) or _glob_touches_denied(line):
            return "reads a secret-bearing file or dumps the environment"
    return None


def _scan_script_file(path: str) -> str | None:
    if _is_trusted_script(path):
        return None
    try:
        p = os.path.expanduser(path.strip().strip("\"'"))
        if not os.path.isfile(p) or os.path.getsize(p) > _MAX_SCRIPT_BYTES:
            return None
        with open(p, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except (OSError, ValueError):
        return None
    what = _text_reason(text)
    return SCRIPT_FILE_MSG.format(what=what) if what else None


def check_bash_command(command: str, _depth: int = 0) -> str | None:
    """Reason to block, or None."""
    if not command or _depth > _MAX_DEPTH:
        return None
    rules = secret_findings(command)
    if rules:
        return SECRET_VALUE_MSG.format(rules=", ".join(rules))
    if _DENIED_TOKEN_RE.search(command) or _ENV_REF_RE.search(command):
        return EXPOSES_MSG.format(what="a secret-reading token or credential variable")
    if _ENV_DUMP_RE.search(command):
        return EXPOSES_MSG.format(what="an environment dump")
    if _GIT_CONFIG_DUMP_RE.search(command):
        return EXPOSES_MSG.format(what="git config or remote URLs may embed credentials")
    reason = _encoded_reason(command)
    if reason:
        return reason
    segments = split_segments_ops(command)
    for idx, (segment, op) in enumerate(segments):
        reason = _dump_reason(segment)
        if reason:
            return reason
        inner = _inner_command(segment)
        if inner:
            reason = check_bash_command(inner, _depth + 1)
            if reason:
                return reason
        script = _script_arg(segment)
        if script:
            reason = _scan_script_file(script)
            if reason:
                return reason
        if _touches_denied_path(segment) or _glob_touches_denied(segment):
            if not _metadata_only(segment):
                return SECRET_FILE_MSG
            if op in _FLOW_OPS and idx > 0 and not _metadata_only(segments[idx - 1][0]):
                return SECRET_FILE_MSG
            if idx + 1 < len(segments) and segments[idx + 1][1] == "|" and not _metadata_only(segments[idx + 1][0]):
                return SECRET_FILE_MSG
    return None


__all__ = ["check_bash_command", "secret_findings", "split_segments", "split_segments_ops"]

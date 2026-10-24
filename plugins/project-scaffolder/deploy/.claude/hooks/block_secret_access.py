#!/usr/bin/env python3
"""PreToolUse hook: block Bash commands that touch secret-bearing files.

Permission deny rules cover the Read tool, but Bash is a different surface.
A deny list there only blocks the exact spellings you thought of, while the
allow list hands out a dozen other ways to read the same bytes -- `head`,
`tail`, `grep`, `python -c`, and so on. Claude Code's own docs call
argument-constraining Bash patterns fragile, and point at a PreToolUse hook
as the way to actually block something: a hook exiting 2 stops the call
before permission rules are evaluated, so it beats allow rules too.

Exit codes:
  0  allow (also used when input is unparseable -- not our business)
  2  block, with the reason on stderr for Claude to read
"""

from __future__ import annotations

import json
import re
import sys

# Each pattern matches a filename that should never appear in a Bash command.
# Kept deliberately narrow: a false block is worse than a missed exotic spelling,
# because the Read-tool deny rules still cover the ordinary path.
SECRET_FILE_PATTERNS = [
    # .env and .env.local, but never .env.example (committed, safe, useful)
    r"(?<![\w.\-])\.env(?!\.example\b)(?:\.[\w\-]+)?(?![\w.])",
    r"(?<![\w\-])secrets\.json\b",
    r"(?<![\w\-])appsettings\.[Ll]ocal\.json\b",
    r"(?<![\w\-])local\.settings\.json\b",
    r"\.(?:pem|pfx|p12)(?![\w])",
]

_COMPILED = [re.compile(p) for p in SECRET_FILE_PATTERNS]

DENIAL = (
    "Blocked: this command references a secret-bearing file.\n"
    "You cannot read or modify .env — that is enforced, not advisory.\n"
    "Instead:\n"
    "  - to see WHICH keys are set (names only, never values):\n"
    "      pwsh -File scripts/secure/Test-Readiness.ps1\n"
    "  - to get a key filled in: ask the developer to run\n"
    "      pwsh -File scripts/secure/Set-ProjectSecrets.ps1\n"
    "    in their own terminal. You cannot run it — your stdin is the null device.\n"
    "  - `.env.example` is committed and safe to read for key names."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in {"Bash", "PowerShell"}:
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not isinstance(command, str):
        return 0

    for pattern in _COMPILED:
        if pattern.search(command):
            print(DENIAL, file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())

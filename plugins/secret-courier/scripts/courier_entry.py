"""Entry point for the hooks and the CLI, run as ``python -I -X utf8 -B courier_entry.py <mode> ...`` by the
.cmd wrappers with no venv: ``-I`` ignores PYTHONPATH, so this file puts ``<root>/src`` on the path itself.

Hook modes (``--bash-hook``, ``--read-hook``, ``--write-hook``, ``--prompt-hook``) fail closed: anything that
goes wrong before the guard takes over exits 2 (the tool call is refused), except the prompt hook, which exits
0 so the developer's message survives. The error text is never printed; it could carry the value being guarded.
``--cli`` hands the remaining arguments to ``courier.cli.main``.
"""

from __future__ import annotations

import os
import sys

PROMPT_MODE = "--prompt-hook"
INTERNAL_MSG = "Blocked: the secret-courier guard could not start (internal error), so the call is refused."


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "src"))
    if "--cli" in sys.argv:
        from courier.cli import main as cli_main

        argv = [a for a in sys.argv[1:] if a != "--cli"]
        return cli_main(argv)
    if "--session-start" in sys.argv:
        try:
            from courier.session import main as session_main

            return session_main()
        except BaseException:  # a readiness line must never break a session
            return 0
    try:
        from courier.guard import run

        return run(sys.argv)
    except BaseException:
        if PROMPT_MODE in sys.argv:
            return 0
        print(INTERNAL_MSG, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

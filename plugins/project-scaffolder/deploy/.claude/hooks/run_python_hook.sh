#!/bin/sh
# Launch a Python hook with the first *working* Python 3 on PATH, and fail CLOSED.
#
# Usage (from .claude/settings.json):  sh "<dir>/run_python_hook.sh" "<dir>/hook.py"
# stdin carries the hook payload JSON through to the Python script untouched.
#
# Why this exists: Claude Code treats any hook exit code other than 2 as
# "non-blocking", so a bare `python hook.py` that can't start (exit 127 when
# macOS has only python3; exit 9009 from the Windows Store "python" stub)
# silently lets every tool call through. Here, anything other than a clean
# allow (0) or a deliberate block (2) becomes a block with an explanation.

hook="$1"
if [ -z "$hook" ] || [ ! -f "$hook" ]; then
  echo "Blocked: secret-guard hook script not found at '$hook'. Restore .claude/hooks/ from the scaffold (or remove the PreToolUse hook from .claude/settings.json if you really mean to drop it)." >&2
  exit 2
fi

for interp in "python3" "python" "py -3"; do
  set -f
  # shellcheck disable=SC2086  # deliberate word split: "py -3" -> py, -3
  set -- $interp
  set +f
  command -v "$1" >/dev/null 2>&1 || continue
  # Reject stubs and Python 2: the probe must actually run Python >= 3.8.
  "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' </dev/null >/dev/null 2>&1 || continue
  "$@" "$hook"
  rc=$?
  case "$rc" in
    0|2) exit "$rc" ;;
  esac
  echo "Blocked: the secret-guard hook crashed (exit $rc) under '$interp', so this call was stopped -- the guard fails closed. Ask the developer to run the hook by hand to see the error." >&2
  exit 2
done

echo "Blocked: no working Python 3 interpreter found (tried python3, python, py -3), so the secret-guard hook could not run and this call was stopped -- the guard fails closed. Fix: install Python 3.8+ and make sure 'python3' or 'python' is on PATH (on Windows, disable the Microsoft Store 'App execution aliases' for python if they shadow a real install)." >&2
exit 2

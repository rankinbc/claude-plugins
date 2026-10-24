"""The Claude Code hook entrypoint (facade over ``guard_bash``, ``guard_paths`` and ``guard_write``).

- ``--bash-hook``: PreToolUse for Bash and PowerShell. Reads the tool call JSON on stdin; exits 2 (block) when
  the command carries a secret-shaped value, reads a denied secret file, or prints secret values.
- ``--read-hook``: PreToolUse for Read, Grep and Glob (``file_path`` / ``path`` / ``glob`` / ``pattern``).
- ``--write-hook``: PreToolUse for Write, Edit and NotebookEdit (target path and content).
- ``--prompt-hook``: UserPromptSubmit. ``paste: advise`` injects the interceptor as context and lets the
  message through; ``paste: block`` refuses it so the value never enters the model's context.

Exit codes: 0 allow, 2 block. Findings never echo the secret. The tool hooks fail CLOSED: a malformed payload
or any internal error exits 2 (``run``); the prompt hook fails open so the developer's message survives.
"""

from __future__ import annotations

import json
import re
import sys

from courier import policy as policy_module
from courier.guard_bash import check_bash_command, secret_findings
from courier.guard_paths import check_glob, check_read_path
from courier.guard_write import check_write

INTERNAL_ERROR_MSG = (
    "Blocked: the secret-courier guard could not evaluate this call (internal error), so it is refused."
)
NO_COMMAND_MSG = "Blocked: the secret-courier guard received no command to check."
PROMPT_BLOCK_MSG = (
    "Blocked: the message carries a secret-shaped value ({rules}) and was not delivered (guard policy paste: block). "
    "Store the value with `courier prompt <name>` and send the NAME instead."
)
PROMPT_ADVICE = (
    "[secret-courier paste interceptor] The message appears to contain a secret-shaped value ({rules}). Do not use, "
    "repeat, store, or reason with the value. Explain in one short paragraph why it must not be in the transcript, "
    "then run `courier prompt <name>` so the developer enters it in a masked console prompt, and continue with "
    "the NAME."
)
# Background-agent completion notices carry tool ids that read as high-entropy tokens; they are harness traffic.
_HARNESS_NOISE_RE = re.compile(r"(?s)<task-notification>.*?</task-notification>|\btoolu_\w+|\bagentId:\s*\S+")


def prompt_findings(prompt: str) -> list[str]:
    return secret_findings(_HARNESS_NOISE_RE.sub("", prompt or ""))


def prompt_context(prompt: str) -> str | None:
    rules = prompt_findings(prompt)
    return PROMPT_ADVICE.format(rules=", ".join(rules)) if rules else None


def _read_stdin_json() -> dict | None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else None
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _tool_input(payload: dict | None) -> dict | None:
    if payload is None:
        return None
    ti = payload.get("tool_input")
    return ti if isinstance(ti, dict) else None


def _block(reason: str) -> int:
    print(reason, file=sys.stderr)
    return 2


def _bash_hook() -> int:
    ti = _tool_input(_read_stdin_json())
    command = ti.get("command") if ti else None
    if not isinstance(command, str) or not command.strip():
        return _block(NO_COMMAND_MSG)
    reason = check_bash_command(command)
    return _block(reason) if reason else 0


def _read_hook() -> int:
    ti = _tool_input(_read_stdin_json())
    if ti is None:
        return _block(INTERNAL_ERROR_MSG)
    for key in ("file_path", "path", "notebook_path"):
        reason = check_read_path(str(ti.get(key) or ""))
        if reason:
            return _block(reason)
    for key in ("glob", "pattern"):
        reason = check_glob(str(ti.get(key) or ""))
        if reason:
            return _block(reason)
    return 0


def _write_hook() -> int:
    ti = _tool_input(_read_stdin_json())
    if ti is None:
        return _block(INTERNAL_ERROR_MSG)
    path = str(ti.get("file_path") or ti.get("notebook_path") or "")
    content = ti.get("content") if ti.get("content") is not None else ti.get("new_source")
    reason = check_write(path, content, ti.get("old_string"), ti.get("new_string"))
    return _block(reason) if reason else 0


def _prompt_hook() -> int:
    payload = _read_stdin_json() or {}
    prompt = str(payload.get("prompt", ""))
    ctx = prompt_context(prompt)
    if not ctx:
        return 0
    if policy_module.POLICY.paste == "block":
        return _block(PROMPT_BLOCK_MSG.format(rules=", ".join(prompt_findings(prompt))))
    print(ctx)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    if "--bash-hook" in argv:
        return _bash_hook()
    if "--read-hook" in argv:
        return _read_hook()
    if "--write-hook" in argv:
        return _write_hook()
    if "--prompt-hook" in argv:
        return _prompt_hook()
    return _block("Blocked: unknown guard mode.")


def run(argv: list[str] | None = None) -> int:
    """``main`` wrapped so the hook fails closed (exit 2) except in prompt mode (exit 0); the error itself is
    never printed, it could carry the value being guarded."""
    argv = sys.argv if argv is None else argv
    try:
        return main(argv)
    except BaseException:
        if "--prompt-hook" in argv:
            return 0
        return _block(INTERNAL_ERROR_MSG)


__all__ = [
    "INTERNAL_ERROR_MSG",
    "PROMPT_BLOCK_MSG",
    "check_bash_command",
    "main",
    "prompt_context",
    "prompt_findings",
    "run",
]

if __name__ == "__main__":
    sys.exit(run())

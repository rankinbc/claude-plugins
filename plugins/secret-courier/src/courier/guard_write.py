"""Write / Edit / NotebookEdit guard: ``check_write(path, content, old_string, new_string, edits)``.

The target path may not be a secret-bearing file, a secret directory, or inside a secret-courier protected root
(the plugin's install dir or ~/.secret-courier), whatever the content. The content (``content`` for Write,
``new_string`` for Edit, ``new_source`` for NotebookEdit, every ``edits[].new_string`` for MultiEdit) may not
carry a value-dumping token, so "write a script that prints the value, then run it" stops at the write. The
*value-shape* content check (a secret-looking literal) is skipped for paths that legitimately hold token-shaped
text (test suites, lock files); the dump-token check and the path deny never are, so a test file can hold a fake
PAT fixture but never a `ConvertFrom-SecureString` dumper.
"""

from __future__ import annotations

import re

from courier.guard_paths import canonical_forms, is_denied_path, is_write_protected
from courier.policy import POLICY
from courier.scan import scan_text

WRITE_PATH_MSG = (
    "Blocked: that path holds secret values; Claude never writes a secret-bearing file. "
    "Store the value with `courier prompt <name>` and reference it by name (secret-courier)."
)
WRITE_PROTECTED_MSG = (
    "Blocked: that path is inside a secret-courier protected root (the plugin's install dir or ~/.secret-courier). "
    "The guard config, hooks, ops and the stores/ledger are never written or edited by Claude (secret-courier)."
)
WRITE_CONTENT_MSG = (
    "Blocked: the content carries {what}. Store the value with `courier prompt <name>` and deliver it with "
    "`courier run` or `courier inject`; scripts that print or decrypt secret values are never written (secret-courier)."
)
_EXEMPT_RE = re.compile(
    r"(?i)(?:^|/)tests?/"
    r"|(?:^|/)(?:package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|"
    r"cargo\.lock|packages\.lock\.json|composer\.lock|gemfile\.lock)$"
)
_TOKEN_RE = re.compile(r"(?i)(?<![\w-])(?:" + "|".join(POLICY.value_dump_tokens) + r")(?![\w-])")


def _dump_token_reason(text: str | None) -> str | None:
    if text and _TOKEN_RE.search(text):
        return WRITE_CONTENT_MSG.format(what="a token that prints or decrypts secret values")
    return None


def _value_shape_reason(text: str | None) -> str | None:
    if not text:
        return None
    rules = sorted({f.rule for f in scan_text(text)})
    if rules:
        return WRITE_CONTENT_MSG.format(what="a secret-shaped value (" + ", ".join(rules) + ")")
    return None


def content_reason(text: str | None) -> str | None:
    """A value-shape or a dump token (used by the content check and by tests)."""
    return _value_shape_reason(text) or _dump_token_reason(text)


def check_write(
    path: str,
    content: str | None,
    old_string: str | None,
    new_string: str | None,
    edits: list | None = None,
) -> str | None:
    if path and is_denied_path(path):
        return WRITE_PATH_MSG
    if path and is_write_protected(path):
        return WRITE_PROTECTED_MSG
    contents = [content, new_string]
    for edit in edits or []:
        if isinstance(edit, dict):
            contents.append(edit.get("new_string"))
    # the dump-token check always runs, even in a tests/ or lock-file path: there is no legitimate reason to
    # write code that decrypts or prints a secret into a test.
    for text in contents:
        reason = _dump_token_reason(text)
        if reason:
            return reason
    if path and any(_EXEMPT_RE.search(form) for form in canonical_forms(path)):
        return None
    for text in contents:
        reason = _value_shape_reason(text)
        if reason:
            return reason
    return None


__all__ = ["WRITE_CONTENT_MSG", "WRITE_PATH_MSG", "WRITE_PROTECTED_MSG", "check_write", "content_reason"]

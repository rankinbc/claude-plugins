"""Write / Edit / NotebookEdit guard: ``check_write(path, content, old_string, new_string)``.

The target path may not be a secret-bearing file or directory, whatever the content. The content (``content``
for Write, ``new_string`` for Edit, ``new_source`` for NotebookEdit) may not carry a secret-shaped value or a
value-dumping token, so "write a script that prints the value, then run it" stops at the write. The content
check is skipped for paths that legitimately hold token-shaped text (test suites, lock files); the path deny
never is.
"""

from __future__ import annotations

import re

from courier.guard_paths import canonical_forms, is_denied_path
from courier.policy import POLICY
from courier.scan import scan_text

WRITE_PATH_MSG = (
    "Blocked: that path holds secret values; Claude never writes a secret-bearing file. "
    "Store the value with `courier prompt <name>` and reference it by name (secret-courier)."
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


def content_reason(text: str | None) -> str | None:
    if not text:
        return None
    rules = sorted({f.rule for f in scan_text(text)})
    if rules:
        return WRITE_CONTENT_MSG.format(what="a secret-shaped value (" + ", ".join(rules) + ")")
    if _TOKEN_RE.search(text):
        return WRITE_CONTENT_MSG.format(what="a token that prints or decrypts secret values")
    return None


def check_write(path: str, content: str | None, old_string: str | None, new_string: str | None) -> str | None:
    if path and is_denied_path(path):
        return WRITE_PATH_MSG
    if path and any(_EXEMPT_RE.search(form) for form in canonical_forms(path)):
        return None
    return content_reason(content) or content_reason(new_string)


__all__ = ["WRITE_CONTENT_MSG", "WRITE_PATH_MSG", "check_write", "content_reason"]

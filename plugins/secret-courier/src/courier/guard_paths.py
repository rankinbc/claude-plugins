"""Secret-bearing file families and path canonicalisation, shared by the Read/Grep/Glob, Bash and Write hooks.

The policy's families are matched against a canonical form of the path (separators, trailing " ." on each
component, ``~``/``$HOME`` prefixes, 8.3 short names and symlinks via ``os.path.realpath`` when the path
exists, lower-case), so ``ENV~1`` and ``.env.`` do not slip past.
"""

from __future__ import annotations

import os
import re

from courier.policy import POLICY, Policy

READ_BLOCK_MSG = (
    "Blocked: that file holds secret values, and Claude handles names only. `courier exists <name>` says where a "
    "value is held; `courier run --env VAR=<store>:<name> -- <command>` or `courier inject` deliver it to a program "
    "without showing it (secret-courier)."
)

_HOME_PREFIX_RE = re.compile(
    r"(?i)^(?:~|\$HOME|\$\{HOME\}|%USERPROFILE%|\$env:USERPROFILE|\$\{env:USERPROFILE\})(?=/|$)"
)
_COPY_SUFFIX = r"(?:\.(?:bak|backup|old|orig|tmp|save))?~?"
_BRACE_RE = re.compile(r"\{([^{}]*)\}")
_MAX_BRACE_ALTERNATIVES = 64


def denied_file_re(policy: Policy = POLICY) -> re.Pattern[str]:
    families = "|".join(policy.denied_file_families)
    dirs = "|".join(re.escape(d) for d in policy.denied_dirs)
    return re.compile(rf"(?i)(?:^|/)(?:{families}){_COPY_SUFFIX}$|(?:^|/)(?:{dirs})(?:/|$)")


def allowed_file_re(policy: Policy = POLICY) -> re.Pattern[str]:
    files = "|".join(policy.allowed_files) or "(?!)"
    dirs = "|".join(re.escape(d) for d in policy.allowed_dirs) or "(?!)"
    return re.compile(rf"(?i)(?:^|/)(?:{files})$|(?:^|/)(?:{dirs})/")


DENIED_FILE_RE = denied_file_re()
ALLOWED_FILE_RE = allowed_file_re()


def _normalise(raw: str) -> str:
    p = raw.strip().strip("\"'").replace("\\", "/")
    if not p:
        return ""
    p = _HOME_PREFIX_RE.sub(lambda _m: os.path.expanduser("~").replace("\\", "/"), p)
    parts = [seg if seg in (".", "..") else seg.rstrip(" .") for seg in p.split("/")]
    p = "/".join(parts)
    p = os.path.normpath(p).replace("\\", "/") if p.strip("/") else p
    return p.lower()


def canonical_forms(raw: str) -> list[str]:
    """The normalised string and, when the path exists, its real path (long names, resolved links)."""
    base = _normalise(raw)
    if not base:
        return []
    forms = [base]
    try:
        if os.path.exists(base):
            real = os.path.realpath(base).replace("\\", "/").lower()
            if real != base:
                forms.append(real)
    except (OSError, ValueError):
        pass
    return forms


def is_denied_path(raw: str) -> bool:
    for form in canonical_forms(raw):
        if ALLOWED_FILE_RE.search(form):
            continue
        if DENIED_FILE_RE.search(form):
            return True
    return False


def check_read_path(path: str) -> str | None:
    if not path:
        return None
    return READ_BLOCK_MSG if is_denied_path(path) else None


def _expand_braces(pattern: str) -> list[str]:
    m = _BRACE_RE.search(pattern)
    if not m:
        return [pattern]
    out: list[str] = []
    for alt in m.group(1).split(","):
        out.extend(_expand_braces(pattern[: m.start()] + alt + pattern[m.end() :]))
        if len(out) >= _MAX_BRACE_ALTERNATIVES:
            break
    return out[:_MAX_BRACE_ALTERNATIVES]


def check_glob(pattern: str) -> str | None:
    """A Grep ``glob`` or Glob ``pattern`` that selects a denied family (``**/.env*``, ``*.{cs,env}``) is a read."""
    if not pattern:
        return None
    for alt in _expand_braces(pattern):
        trimmed = alt.strip().rstrip("*?")
        if not trimmed:
            continue
        for form in {trimmed, re.sub(r"(^|/)[*?]+", r"\1", trimmed)}:
            if form.strip("/") and is_denied_path(form):
                return READ_BLOCK_MSG
    return None


__all__ = [
    "ALLOWED_FILE_RE",
    "DENIED_FILE_RE",
    "READ_BLOCK_MSG",
    "canonical_forms",
    "check_glob",
    "check_read_path",
    "is_denied_path",
]

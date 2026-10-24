"""Secret-bearing file families and path canonicalisation, shared by the Read/Grep/Glob, Bash and Write hooks.

The policy's families are matched against a canonical form of the path (separators, trailing " ." on each
component, ``~``/``$HOME`` prefixes, 8.3 short names and symlinks via ``os.path.realpath`` when the path
exists, lower-case), so ``ENV~1`` and ``.env.`` do not slip past.
"""

from __future__ import annotations

import os
import re

from courier.paths import DIR_NAME, home, plugin_root
from courier.policy import POLICY, Policy

READ_BLOCK_MSG = (
    "Blocked: that file holds secret values, and Claude handles names only. `courier exists <name>` says where a "
    "value is held; `courier run --env VAR=<store>:<name> -- <command>` or `courier inject` deliver it to a program "
    "without showing it (secret-courier)."
)
WRITE_PROTECTED_MSG = (
    "Blocked: that path is inside a secret-courier protected root (the plugin's own install dir or "
    "~/.secret-courier). The guard config, hooks, ops and the stores/ledger are never written or edited by Claude; "
    "a human edits them directly (secret-courier)."
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


def _strip_ads(component: str) -> str:
    """Drop an NTFS alternate-data-stream suffix on a filename (``.env:stream`` / ``.env::$DATA`` -> ``.env``).
    The colon never belongs to a bare filename, so stripping it cannot hide a legitimate path."""
    if ":" in component:
        return component.split(":", 1)[0]
    return component


def _normalise(raw: str) -> str:
    p = raw.strip().strip("\"'").replace("\\", "/")
    if not p:
        return ""
    p = _HOME_PREFIX_RE.sub(lambda _m: os.path.expanduser("~").replace("\\", "/"), p)
    unc = p.startswith("//")
    parts = [seg if seg in (".", "..") else seg.rstrip(" .") for seg in p.split("/")]
    if parts:
        # an ADS rides on the final filename; the first component may be a drive letter ("c:")
        parts[-1] = _strip_ads(parts[-1])
    p = "/".join(parts)
    if not unc:
        p = os.path.normpath(p).replace("\\", "/") if p.strip("/") else p
    return p.lower()


def _is_lexical_only(form: str) -> bool:
    """UNC (``//host/share``) and device (``//./`` ``//?/``) paths: resolving or stat'ing them reaches out over
    the network (which can leak an NTLM hash) or to a device, so they are evaluated lexically and never touched."""
    return form.startswith("//")


def canonical_forms(raw: str) -> list[str]:
    """The normalised string and, when the path exists on disk, its real path (long names, resolved links). A UNC
    or device path is returned lexically only; the filesystem is never touched for it (NTLM-hash leak)."""
    base = _normalise(raw)
    if not base:
        return []
    forms = [base]
    if _is_lexical_only(base):
        return forms
    try:
        if os.path.exists(base):
            real = os.path.realpath(base).replace("\\", "/").lower()
            if real != base:
                forms.append(real)
    except (OSError, ValueError):
        pass
    return forms


def _norm_root(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def protected_write_roots() -> list[str]:
    """Roots Claude may never write or edit: the plugin's own install dir (guard config, hooks, ops, the guard
    code itself) and ~/.secret-courier (stores, ledger, manifest, overlay). Computed per call so COURIER_HOME is
    honoured. The ~/.secret-courier directory is also in denied_dirs, so the default home is covered even when
    COURIER_HOME points elsewhere."""
    import contextlib

    roots = [_norm_root(str(plugin_root()))]
    with contextlib.suppress(OSError, ValueError, RuntimeError):
        roots.append(_norm_root(str(home())))
    return [r for r in roots if r]


_STATE_DIR = DIR_NAME.lower()


def is_write_protected(raw: str) -> bool:
    roots = protected_write_roots()
    for form in canonical_forms(raw):
        # the courier state directory is protected wherever it is, regardless of COURIER_HOME: writing the
        # overlay, stores or ledger is never the model's to do. The allow list (read-only metadata) never
        # reaches here, so a Write/Edit to ~/.secret-courier/guard-policy.json is always refused.
        segments = form.split("/")
        if _STATE_DIR in segments:
            return True
        for root in roots:
            if form == root or form.startswith(root + "/"):
                return True
    return False


def is_denied_path(raw: str) -> bool:
    """Deny is evaluated before allow: a form that matches a denied family/dir is denied, and the allow list may
    rescue it only when it matches an anchored, value-free metadata file (``.env.example``, the courier home's
    manifest/sinks/audit/config/overlay). The allow list can never un-deny a secret-bearing file."""
    return any(DENIED_FILE_RE.search(form) and not ALLOWED_FILE_RE.search(form) for form in canonical_forms(raw))


def check_read_path(path: str) -> str | None:
    if not path:
        return None
    return READ_BLOCK_MSG if is_denied_path(path) else None


CONTENT_GREP_MSG = (
    "Blocked: a content-mode Grep over a directory tree would print lines from any secret-bearing file in it "
    "(e.g. .env). Grep a specific non-secret file, or use the default files-with-matches mode (names only). "
    "`courier exists <name>` and `courier run` deliver a value without printing it (secret-courier)."
)


def _looks_like_file(form: str) -> bool:
    """A specific file (safe to grep) rather than a directory tree. Uses the filesystem when it can, and falls
    back to 'has a file extension' lexically (never touching a UNC/device path)."""
    if not _is_lexical_only(form):
        try:
            if os.path.isfile(form):
                return True
            if os.path.isdir(form):
                return False
        except (OSError, ValueError):
            pass
    base = form.rstrip("/").split("/")[-1]
    return "." in base and not base.endswith(".")


def check_grep_content(path: str, output_mode: str) -> str | None:
    """Grep in ``content`` output mode returns matching lines, so a tree walk leaks values. Allow it only against
    a single specific file; deny an empty path (the working-directory tree), a glob, or a directory."""
    if output_mode != "content":
        return None
    raw = (path or "").strip()
    if not raw:
        return CONTENT_GREP_MSG
    if any(c in raw for c in "*?["):
        return CONTENT_GREP_MSG
    form = _normalise(raw)
    return None if _looks_like_file(form) else CONTENT_GREP_MSG


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
    "WRITE_PROTECTED_MSG",
    "canonical_forms",
    "check_glob",
    "check_read_path",
    "is_denied_path",
    "is_write_protected",
    "protected_write_roots",
]

"""The guard policy: every deny list the hooks and the PowerShell ops share, from ``config/guard-policy.json``
plus an optional developer overlay (``~/.secret-courier/guard-policy.json``).

Stdlib only: the hook imports this under ``python -I`` with no venv. The overlay may ADD entries to a list
field and set ``paste`` (``advise`` | ``block``); any other key, a wrong type or a broken file is reported in
``Policy.overlay_problems`` (``courier doctor`` shows them) and otherwise ignored, so a bad overlay can never
weaken the shipped lists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from courier.paths import plugin_root, policy_overlay

DEFAULT_PATH = plugin_root() / "config" / "guard-policy.json"
PASTE_MODES = ("advise", "block")

_LIST_FIELDS = (
    "denied_file_families",
    "denied_dirs",
    "denied_samples",
    "allowed_files",
    "allowed_dirs",
    "value_dump_tokens",
    "interpreters",
    "metadata_programs",
    "safe_git",
    "trusted_script_dirs",
)

# An overlay may only TIGHTEN the guard: it can add entries to these deny lists and nothing else. Adding to
# allowed_files/allowed_dirs (un-denies a file), to metadata_programs/safe_git/trusted_script_dirs/interpreters
# (treats more commands as safe), or changing secret_env_names would all WEAKEN the shipped policy, so the merge
# refuses them. This is what SECURITY.md promises: the shipped lists can never be relaxed from the home dir.
_TIGHTEN_ONLY_FIELDS = (
    "denied_file_families",
    "denied_dirs",
    "denied_samples",
    "value_dump_tokens",
)


@dataclass(frozen=True)
class Policy:
    denied_file_families: tuple[str, ...]
    denied_dirs: tuple[str, ...]
    denied_samples: tuple[str, ...]
    allowed_files: tuple[str, ...]
    allowed_dirs: tuple[str, ...]
    secret_env_names: str
    value_dump_tokens: tuple[str, ...]
    interpreters: tuple[str, ...]
    metadata_programs: tuple[str, ...]
    safe_git: tuple[str, ...]
    trusted_script_dirs: tuple[str, ...]
    paste: str = "advise"
    overlay_problems: tuple[str, ...] = field(default_factory=tuple)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _str_list(value: Any) -> list[str] | None:
    return value if isinstance(value, list) and all(isinstance(v, str) for v in value) else None


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    merged = dict(base)
    problems: list[str] = []
    for key, value in overlay.items():
        if key in _TIGHTEN_ONLY_FIELDS:
            extra = _str_list(value)
            if extra is None:
                problems.append(f"{key}: not a list of strings; ignored")
                continue
            merged[key] = list(base.get(key, [])) + [v for v in extra if v not in base.get(key, [])]
        elif key in _LIST_FIELDS:
            problems.append(f"{key}: an overlay may only add denies, never relax the guard; ignored")
        elif key == "paste":
            if value in PASTE_MODES:
                merged[key] = value
            else:
                problems.append(f"paste: must be one of {', '.join(PASTE_MODES)}; ignored")
        elif key == "description":
            continue
        else:
            problems.append(f"{key}: not overridable; ignored")
    return merged, problems


def _build(data: dict[str, Any], problems: list[str]) -> Policy:
    return Policy(
        denied_file_families=tuple(data["denied_file_families"]),
        denied_dirs=tuple(data["denied_dirs"]),
        denied_samples=tuple(data.get("denied_samples", ())),
        allowed_files=tuple(data.get("allowed_files", ())),
        allowed_dirs=tuple(data.get("allowed_dirs", ())),
        secret_env_names=str(data["secret_env_names"]),
        value_dump_tokens=tuple(data["value_dump_tokens"]),
        interpreters=tuple(data["interpreters"]),
        metadata_programs=tuple(data["metadata_programs"]),
        safe_git=tuple(data["safe_git"]),
        trusted_script_dirs=tuple(data.get("trusted_script_dirs", ())),
        paste=str(data.get("paste", "advise")),
        overlay_problems=tuple(problems),
    )


def load(user_overlay: Path | None = None, default_path: Path = DEFAULT_PATH) -> Policy:
    """The shipped policy with ``user_overlay`` applied (add-only). A missing or unreadable overlay is ignored."""
    base = _read_json(default_path)
    if base is None:
        raise RuntimeError(f"guard policy missing or invalid: {default_path}")
    problems: list[str] = []
    if user_overlay is not None and user_overlay.exists():
        overlay = _read_json(user_overlay)
        if overlay is None:
            problems.append(f"{user_overlay}: not a JSON object; ignored")
        else:
            base, problems = _merge(base, overlay)
    return _build(base, problems)


POLICY: Policy = load(policy_overlay())

__all__ = ["DEFAULT_PATH", "PASTE_MODES", "POLICY", "Policy", "load"]

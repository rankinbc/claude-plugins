"""Where secret-courier keeps its own state: ``~/.secret-courier`` (or ``$COURIER_HOME``). Names and ledgers
only ever live here in plaintext; values are DPAPI blobs (the PowerShell side owns them)."""

from __future__ import annotations

import os
from pathlib import Path

ENV_HOME = "COURIER_HOME"
DIR_NAME = ".secret-courier"


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[2]


def home() -> Path:
    raw = os.environ.get(ENV_HOME)
    return Path(raw) if raw else Path.home() / DIR_NAME


def policy_overlay() -> Path:
    return home() / "guard-policy.json"


def config_file() -> Path:
    return home() / "config.json"


def sinks_file() -> Path:
    return home() / "sinks.json"


def audit_file() -> Path:
    return home() / "audit.jsonl"


__all__ = ["DIR_NAME", "ENV_HOME", "audit_file", "config_file", "home", "plugin_root", "policy_overlay", "sinks_file"]

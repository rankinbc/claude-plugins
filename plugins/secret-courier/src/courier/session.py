"""SessionStart: one line that says whether the guard is live on this machine, so a developer never wonders.

Printed as a Claude Code ``systemMessage`` (shown to the person, not added to the model's context). Cheap on
purpose: no subprocesses except ``pwsh`` lookup; the fail-closed probe belongs to ``courier doctor``.
"""

from __future__ import annotations

import json
import shutil
import sys

from courier import __version__
from courier.policy import POLICY


def readiness() -> str:
    v = sys.version_info
    parts = [
        f"secret-courier {__version__}: guard hooks active (Python {v.major}.{v.minor}, paste policy {POLICY.paste})"
    ]
    if not shutil.which("pwsh"):
        parts.append(
            "PowerShell 7 is not on PATH, so the courier commands (prompt, copy, inject, run) will refuse until "
            "it is installed: winget install Microsoft.PowerShell"
        )
    if POLICY.overlay_problems:
        parts.append("the policy overlay was ignored in part; run `courier doctor`")
    return ". ".join(parts) + "."


def main() -> int:
    print(json.dumps({"systemMessage": readiness()}))
    return 0


__all__ = ["main", "readiness"]

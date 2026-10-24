"""The SessionStart readiness line and its wiring. courier-scan: ignore-file"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_session_start_prints_one_system_message():
    proc = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-B", str(ROOT / "scripts" / "courier_entry.py"), "--session-start"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip())
    assert "guard hooks active" in payload["systemMessage"]


def test_session_start_hook_is_wired():
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    commands = [h["command"] for e in hooks["SessionStart"] for h in e["hooks"]]
    assert any("courier-session.cmd" in c for c in commands)
    assert (ROOT / "scripts" / "courier-session.cmd").exists()

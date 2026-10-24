"""The wrapper, the entry script, the hook wiring and the policy overlay. courier-scan: ignore-file"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from courier import policy

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "scripts" / "courier_entry.py"
WRAPPER = ROOT / "scripts" / "courier-guard.cmd"


def _hooks() -> dict:
    return json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]


def test_hooks_cover_every_tool_and_block_on_failure():
    covered: dict[str, set[str]] = {}
    for entry in _hooks()["PreToolUse"]:
        for h in entry["hooks"]:
            assert h.get("onFailure") == "block", entry["matcher"]
            mode = next(f for f in ("--write-hook", "--read-hook", "--bash-hook") if f in h["command"])
            covered.setdefault(mode, set()).update(entry["matcher"].split("|"))
    assert {"Bash", "PowerShell"} <= covered["--bash-hook"]
    assert {"Read", "Grep", "Glob"} <= covered["--read-hook"]
    assert {"Write", "Edit", "NotebookEdit"} <= covered["--write-hook"]
    prompt = [h for e in _hooks()["UserPromptSubmit"] for h in e["hooks"]]
    assert prompt and all("--prompt-hook" in h["command"] and "onFailure" not in h for h in prompt)


def test_guard_chain_is_stdlib_only():
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); before=set(sys.modules); import courier.guard; "
        "new=[m for m in sys.modules if m not in before]; "
        "third=[m for m in new if not m.startswith(('courier','_')) "
        "and m.split('.')[0] not in sys.stdlib_module_names]; "
        "print(third)"
    )
    out = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-B", "-c", code, str(ROOT / "src")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert out == "[]", out


def test_entry_script_blocks_a_denied_read_and_allows_git_status():
    proc = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-B", str(ENTRY), "--read-hook"],
        input=json.dumps({"tool_input": {"file_path": str(ROOT / ".env")}}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2 and "Blocked" in proc.stderr
    proc = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-B", str(ENTRY), "--bash-hook"],
        input=json.dumps({"tool_input": {"command": "git status"}}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


@pytest.mark.skipif(sys.platform != "win32", reason="cmd wrapper")
def test_wrapper_fails_closed_without_python(tmp_path: Path):
    scripts = tmp_path / "plugin" / "scripts"
    scripts.mkdir(parents=True)
    shutil.copyfile(WRAPPER, scripts / "courier-guard.cmd")
    env = {k: v for k, v in os.environ.items() if k != "COURIER_PYTHON"}
    env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    for mode, expected in (("--bash-hook", 2), ("--prompt-hook", 0)):
        proc = subprocess.run(
            ["cmd", "/c", str(scripts / "courier-guard.cmd"), mode],
            input='{"tool_input":{"command":"echo hi"}}',
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
            check=False,
        )
        assert proc.returncode == expected, (mode, proc.returncode, proc.stderr)
        assert "No such file or directory" not in proc.stderr
    env2 = dict(os.environ)
    env2["COURIER_PYTHON"] = sys.executable
    proc = subprocess.run(
        ["cmd", "/c", str(WRAPPER), "--bash-hook"],
        input='{"tool_input":{"command":"type .env"}}',
        capture_output=True,
        text=True,
        env=env2,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 2, (proc.returncode, proc.stderr)


def test_overlay_only_adds(tmp_path: Path):
    overlay = tmp_path / "guard-policy.json"
    overlay.write_text(
        json.dumps({"denied_dirs": ["extra-dir"], "value_dump_tokens": [], "paste": "block", "secret_env_names": "x"}),
        encoding="utf-8",
    )
    base = policy.load(user_overlay=None)
    merged = policy.load(user_overlay=overlay)
    assert "extra-dir" in merged.denied_dirs and set(base.denied_dirs) <= set(merged.denied_dirs)
    assert merged.value_dump_tokens == base.value_dump_tokens
    assert merged.paste == "block" and base.paste == "advise"
    assert merged.secret_env_names == base.secret_env_names and merged.overlay_problems
    broken = tmp_path / "b.json"
    broken.write_text("{not json", encoding="utf-8")
    assert policy.load(user_overlay=broken).denied_dirs == base.denied_dirs

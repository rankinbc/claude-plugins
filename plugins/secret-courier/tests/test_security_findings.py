"""Regression tests for the security-review findings, including the reviewer's bypass cases.
courier-scan: ignore-file (every secret-shaped string is built at runtime)."""

from __future__ import annotations

import io
import json

import pytest

from courier import bridge, guard, policy
from courier.guard_bash import check_bash_command
from courier.guard_paths import (
    canonical_forms,
    check_grep_content,
    is_denied_path,
    is_write_protected,
)
from courier.guard_write import check_write
from courier.paths import plugin_root
from tests import fixtures as fx


def _blocked(cmd: str) -> bool:
    return check_bash_command(cmd) is not None


# --- finding 1: guard config and store are not the model's to write; deny before allow; overlay tightens only ---


@pytest.mark.parametrize(
    "path",
    [
        r"C:\Users\x\.secret-courier\guard-policy.json",
        r"C:\Users\x\.secret-courier\config.json",
        r"C:\Users\x\.secret-courier\sinks.json",
        r"C:\Users\x\.secret-courier\audit.jsonl",
        r"C:\Users\x\.secret-courier\secrets.json",
        str(plugin_root() / "config" / "guard-policy.json"),
        str(plugin_root() / "hooks" / "hooks.json"),
        str(plugin_root() / "src" / "courier" / "guard_bash.py"),
    ],
)
def test_protected_roots_are_write_denied(path):
    assert is_write_protected(path), path
    assert check_write(path, "{}", None, None) is not None, path


def test_reading_courier_metadata_stays_allowed_but_writing_does_not():
    # config.json / guard-policy.json hold no values, so reading is fine; writing is refused.
    assert not is_denied_path(r"C:\Users\x\.secret-courier\config.json")
    assert check_write(r"C:\Users\x\.secret-courier\config.json", "{}", None, None) is not None


def test_bare_config_json_allow_no_longer_shadows_docker_config():
    assert is_denied_path("C:/Users/x/.docker/config.json")
    # an ordinary project config.json is still writable/readable
    assert not is_denied_path("C:/repo/config.json")
    assert check_write("C:/repo/config.json", "{}", None, None) is None


def test_overlay_may_tighten_but_never_relax(tmp_path):
    weaken = tmp_path / "guard-policy.json"
    weaken.write_text(json.dumps({"allowed_files": [".*"], "metadata_programs": ["cat"]}), encoding="utf-8")
    pol = policy.load(user_overlay=weaken)
    assert ".*" not in pol.allowed_files
    assert "cat" not in pol.metadata_programs
    assert any("only add denies" in p for p in pol.overlay_problems)

    tighten = tmp_path / "tighten.json"
    tighten.write_text(json.dumps({"denied_file_families": ["my-secret\\.conf"]}), encoding="utf-8")
    pol2 = policy.load(user_overlay=tighten)
    assert "my-secret\\.conf" in pol2.denied_file_families


# --- finding 2: endpoints only reach their declared host, over https ---


def _ok_runner(argv, capture):
    return ("STATUS valid 200", "", 0)


def test_endpoint_host_and_scheme_are_validated(monkeypatch):
    monkeypatch.setattr(
        bridge,
        "load_endpoints",
        lambda: {
            "github": {"url": "https://api.github.com/user", "auth": "bearer", "expect": 200},
            "evil": {"url": "https://{org}.example.com/x", "auth": "bearer", "needs": ["org"]},
            "insecure": {"url": "http://api.github.com/user", "auth": "bearer"},
        },
    )
    assert bridge.test("mykey", "github", runner=_ok_runner).status == "valid"
    assert "allowlist" in bridge.test("mykey", "evil", {"org": "attacker"}, runner=_ok_runner).detail
    assert "https" in bridge.test("mykey", "insecure", runner=_ok_runner).detail


# --- finding 3: courier run captures (never inherits) the child's output ---


def test_run_command_captures_child_output():
    seen = {}

    def runner(argv, capture):
        seen["capture"] = capture
        return ("STATUS exit 0", "", 0)

    bridge.run_command({"X": "env:FOO"}, ["echo", "hi"], runner=runner)
    assert seen["capture"] is True


# --- finding 4: decrypt / module-import APIs are denied in commands and in written content ---


@pytest.mark.parametrize(
    "cmd",
    [
        "Import-Module C:/x/secret-courier/powershell/Courier.psm1; Get-CourierStoreValue -Store dpapi -Name k",
        "Import-Module ./powershell/Courier.psm1; [CourierCred]::Read('secret-courier/github-pat')",
        "[Net.NetworkCredential]::new('', (Get-CourierStoreValue dpapi x)).Password",
        "[Security.Cryptography.ProtectedData]::Unprotect($b, $null, 0)",
    ],
)
def test_decrypt_apis_are_blocked(cmd):
    assert _blocked(cmd)


def test_decrypt_apis_blocked_in_written_content_and_tests():
    assert check_write("dump.ps1", "Get-CourierStoreValue -Store dpapi -Name k", None, None) is not None
    # a dump token is refused even under tests/ (no legit reason to write a decrypter into a test)
    assert check_write("tests/dump.ps1", "ConvertFrom-SecureString", None, None) is not None
    # but a fake value fixture under tests/ is still allowed
    assert check_write("tests/test_x.py", f"TOKEN='{fx.fake_pat()}'", None, None) is None


# --- finding 5: shell-scanner bypasses ---


@pytest.mark.parametrize(
    "cmd",
    [
        "cat .[e]nv",  # bracket class
        "cat '.e''nv'",  # quote concatenation
        'cat "$HOME/.ss"h/id_rsa',  # quote concatenation across a path
        "Get-Content '.env::$DATA'",  # NTFS ADS
        "Get-Content *",  # bare-glob directory sweep
        "cat *",
        "grep -ra TOKEN .",  # recursive search of the working tree
        "rg -uu --no-ignore PASSWORD .",
        "findstr /s /i password *",
        "rg SECRET",  # ripgrep defaults to the working tree
        "env -0",  # env dump variant
        "declare -p",
        "cmd /c set G",  # filtered env dump
        "echo $env:github_token",  # case-insensitive env ref
        "echo $env:OPENAI_KEY",
        "python -c \"import os;print(os.getenv('github_token'))\"",
        'node -e "console.log(process.env.GITHUB_TOKEN)"',
    ],
)
def test_reviewer_bash_bypasses_are_blocked(cmd):
    assert _blocked(cmd), cmd


@pytest.mark.parametrize("cmd", ["./sub/dump.ps1", ". ./sub/dump.ps1", "pwsh -File sub/dump.ps1", "python sub/dump.py"])
def test_directly_executed_scripts_are_scanned(tmp_path, monkeypatch, cmd):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "dump.ps1").write_text("ConvertFrom-SecureString $x", encoding="utf-8")
    (sub / "dump.py").write_text("import os\nprint(os.getenv('GITHUB_TOKEN'))", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert check_bash_command(cmd) is not None, cmd


@pytest.mark.parametrize(
    "cmd",
    [
        "git status",
        "grep -rn TODO src | head",  # scoped recursive search stays allowed
        'node -e "console.log(process.env.FOO)"',  # a non-credential variable
        "set -e && make",  # shell option, not an env dump
        "set -euo pipefail",
        "export FOO=bar",
    ],
)
def test_legitimate_commands_still_allowed(cmd):
    assert not _blocked(cmd), cmd


def test_non_extension_interpreter_script_is_scanned(tmp_path, monkeypatch):
    script = tmp_path / "dump.txt"
    script.write_text("ConvertFrom-SecureString", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert check_bash_command("python dump.txt") is not None


def test_oversized_script_fails_closed(tmp_path, monkeypatch):
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 60000, encoding="utf-8")  # > 256 KB
    monkeypatch.chdir(tmp_path)
    assert check_bash_command("python big.py") is not None


def test_multiedit_edits_are_scanned(monkeypatch):
    # check_write inspects every edits[].new_string
    edits = [{"old_string": "a", "new_string": "ConvertFrom-SecureString"}]
    assert check_write("C:/repo/d.ps1", None, None, None, edits) is not None
    # and the write-hook reaches it from the tool payload
    payload = {"tool_input": {"file_path": "C:/repo/d.ps1", "edits": edits}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert guard.main(["g", "--write-hook"]) == 2


# --- finding 7: UNC / device paths are never stat'd, evaluated lexically ---


def test_unc_paths_are_lexical_and_denied():
    assert canonical_forms(r"\\attacker\share\.env") == ["//attacker/share/.env"]  # no realpath appended
    assert is_denied_path(r"\\host\share\.env")
    assert is_denied_path("//host/share/id_rsa")
    assert not is_denied_path("//host/share/readme.md")


# --- finding 5/7: content-mode Grep over a directory is a read ---


def test_content_grep_over_directory_is_blocked():
    assert check_grep_content("C:/repo", "content") is not None
    assert check_grep_content("", "content") is not None
    assert check_grep_content("src/**", "content") is not None
    assert check_grep_content("C:/repo/README.md", "content") is None
    assert check_grep_content("C:/repo", "files_with_matches") is None


# --- finding 8: an oversized command fails closed with a clear message ---


def test_oversized_command_is_blocked():
    reason = check_bash_command("echo " + "a " * 200000)
    assert reason is not None and "too large" in reason


# --- finding 10: courier log never surfaces a value ---


def test_log_output_is_redacted(tmp_path, monkeypatch, capsys):
    home = tmp_path
    monkeypatch.setenv("COURIER_HOME", str(home))
    leaked = fx.fake_storage_key()
    (home / "audit.jsonl").write_text(
        json.dumps({"ts": "t", "op": "run", "status": "exit", "detail": leaked}) + "\n", encoding="utf-8"
    )
    from courier import cli

    cli.main(["log"])
    out = capsys.readouterr().out
    assert leaked[5:30] not in out

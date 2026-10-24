"""Read/Grep/Glob guard: path families, canonical forms, globs. courier-scan: ignore-file"""

from __future__ import annotations

import io
import json

import pytest

from courier import guard
from courier.guard_paths import DENIED_FILE_RE, check_glob, check_read_path
from courier.policy import POLICY


@pytest.mark.parametrize(
    "path",
    [
        r"C:\Users\x\.secret-courier\secrets.json",
        "./.env",
        "/repo/.env.local",
        r"C:\r\Api\appsettings.local.json",
        r"C:\r\local.settings.json",
        r"C:\r\.git\config",
        r"C:\Users\x\.azure\msal.cache",
        r"C:\r\cert.pfx",
        "~/.ssh/id_rsa",
        "~/.netrc",
        "/home/x/.pgpass",
        "infra/terraform.tfvars",
        "android/release.keystore",
        "C:/r/.env.bak",
        "C:/r/.ENV",
        "C:/r/.env.",
        "/proc/self/environ",
    ],
)
def test_secret_files_are_denied(path):
    assert check_read_path(path) is not None, path


@pytest.mark.parametrize(
    "path",
    [
        ".env.example",
        r"C:\Users\x\.secret-courier\secrets.manifest.json",
        r"C:\Users\x\.secret-courier\sinks.json",
        r"C:\r\appsettings.json",
        r"C:\r\src\a.cs",
        r"C:\r\tests\fixtures\m\.env",
        "README.md",
    ],
)
def test_ordinary_files_are_allowed(path):
    assert check_read_path(path) is None, path


def test_glob_pattern_and_braces(monkeypatch):
    def hook(tool_input):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_input": tool_input})))
        return guard.main(["guard", "--read-hook"])

    assert hook({"pattern": "**/.env*", "path": ""}) == 2
    assert hook({"pattern": "**/*.cs"}) == 0
    assert hook({"glob": "**/*.{pem,key}"}) == 2
    assert hook({"glob": "*.{cs,ts}"}) == 0
    assert hook({"file_path": "C:/r/.env"}) == 2
    assert hook({}) == 0
    assert check_glob("{.env,.env.local}") is not None
    assert check_glob("*.env") is not None
    assert check_glob("src/{a,b}/*.py") is None


def test_every_policy_sample_is_a_denied_path():
    stale = [s for s in POLICY.denied_samples if not DENIED_FILE_RE.search(s.lower())]
    assert not stale, stale


def test_malformed_payload_fails_closed(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert guard.main(["guard", "--read-hook"]) == 2
    assert "Blocked" in capsys.readouterr().err

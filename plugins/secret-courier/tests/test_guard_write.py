"""Write / Edit / NotebookEdit guard and the prompt policy. courier-scan: ignore-file"""

from __future__ import annotations

import dataclasses
import io
import json

import pytest

from courier import guard, policy
from courier.guard_write import check_write
from tests import fixtures as fx


@pytest.mark.parametrize(
    "path, kwargs",
    [
        (".env", {"content": "X=1"}),
        (r"C:\r\appsettings.local.json", {"old_string": "a", "new_string": "b"}),
        ("~/.ssh/notes.ipynb", {"content": "print(1)"}),
        (r"C:\Users\x\.secret-courier\secrets.json", {"content": "{}"}),
    ],
)
def test_denied_target_path_is_blocked(path, kwargs):
    assert check_write(path, kwargs.get("content"), kwargs.get("old_string"), kwargs.get("new_string")) is not None


def test_ordinary_writes_are_allowed():
    assert check_write(".env.example", "X=1", None, None) is None
    assert check_write(r"C:\r\src\a.cs", "class A {}", None, None) is None


def test_secret_shaped_content_and_dump_tokens_are_blocked():
    assert check_write("src/x.py", f"TOKEN = '{fx.fake_jwt()}'", None, None) is not None
    assert check_write("src/x.py", None, "old", f"conn = '{fx.fake_storage_conn()}'") is not None
    assert check_write("temp_dump.ps1", "ConvertFrom-SecureString $x | Set-Content out.txt", None, None) is not None
    assert check_write("temp_dump.py", "import keyring\nprint(keyring.get_password('a','b'))", None, None) is not None


def test_lock_files_and_tests_are_exempt_from_the_content_scan():
    integrity = (
        '"integrity": "sha512-'
        + "Qm9yaW5nQmFzZTY0U3RyaW5nVGhhdExvb2tzUmFuZG9tRW5vdWdoVG9UcmlwVGhlRW50cm9weVJ1bGU0MjAx"
        + '=="'
    )
    assert check_write(r"C:\r\package-lock.json", "{" + integrity + "}", None, None) is None
    assert check_write("tests/test_new.py", f"TOKEN = '{fx.fake_jwt()}'", None, None) is None
    assert check_write("tests/.env", "X=1", None, None) is not None


def test_write_hook_payload_shapes(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert guard.main(["guard", "--write-hook"]) == 2
    payload = {
        "tool_input": {"notebook_path": r"C:\r\nb.ipynb", "new_source": f"k = '{fx.fake_jwt()}'", "cell_id": "1"}
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert guard.main(["guard", "--write-hook"]) == 2
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"tool_input": {"file_path": r"C:\r\src\a.py", "content": "print('hi')"}}))
    )
    assert guard.main(["guard", "--write-hook"]) == 0


NOTIFICATION = (
    "<task-notification>\n<task-id>a54ba9ec6af4a34ea</task-id>\n<tool-use-id>toolu_013xTNV92HVKnP259zkoWJvQ</tool-use-id>\n"
    "<result>agentId: ab32e03def42d6940 done</result>\n</task-notification>"
)


def _prompt(text: str, monkeypatch) -> tuple[int, str, str]:
    import sys

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": text})))
    err, out = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    monkeypatch.setattr(sys, "stdout", out)
    rc = guard.main(["guard", "--prompt-hook"])
    return rc, out.getvalue(), err.getvalue()


def test_prompt_policy(monkeypatch):
    assert guard.prompt_context(NOTIFICATION) is None
    secret = fx.fake_storage_key()
    monkeypatch.setattr(policy, "POLICY", dataclasses.replace(policy.POLICY, paste="advise"))
    rc, out, err = _prompt(f"please set the key {secret} on the app", monkeypatch)
    assert rc == 0 and "paste interceptor" in out and secret[5:30] not in out and err == ""
    monkeypatch.setattr(policy, "POLICY", dataclasses.replace(policy.POLICY, paste="block"))
    rc, out, err = _prompt(f"here you go: {secret}", monkeypatch)
    assert rc == 2 and out == "" and "secret-shaped" in err and secret[5:30] not in err
    assert "No such file or directory" not in err
    rc, out, err = _prompt("rename the method and run the tests", monkeypatch)
    assert rc == 0 and out == "" and err == ""

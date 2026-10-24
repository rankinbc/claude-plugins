"""``courier log`` prints the audit entries (names and statuses only). courier-scan: ignore-file"""

from __future__ import annotations

import json

from courier import cli


def test_log_prints_entries_and_handles_an_empty_home(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("COURIER_HOME", str(tmp_path))
    assert cli.main(["log"]) == 0
    assert "no audit log yet" in capsys.readouterr().out
    entries = [
        {"ts": "2026-10-20T00:00:00Z", "op": "exists", "status": "found", "detail": "dpapi"},
        {"ts": "2026-10-20T00:00:01Z", "op": "inject", "status": "stored", "detail": "C:/r/.env keys=1"},
    ]
    (tmp_path / "audit.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\nnot json\n", encoding="utf-8")
    assert cli.main(["log", "-n", "5"]) == 0
    out = capsys.readouterr().out
    assert "exists" in out and "inject" in out and "values are never logged" in out

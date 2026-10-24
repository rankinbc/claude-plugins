"""The bridge and the CLI with a fake runner: name validation, STATUS parsing, redact-or-error, routing.
courier-scan: ignore-file"""

from __future__ import annotations

from courier import bridge, cli, doctor
from tests import fixtures as fx


def runner_returning(stdout: str, code: int = 0, stderr: str = ""):
    calls: list[list[str]] = []

    def run(argv: list[str], capture: bool) -> tuple[str, str, int]:
        calls.append(argv)
        return stdout, stderr, code

    run.calls = calls  # type: ignore[attr-defined]
    return run


def test_exists_parses_status_and_passes_only_the_name():
    r = runner_returning("STATUS found dpapi\n")
    res = bridge.exists("my-api-key", runner=r)
    assert res.status == "found" and res.detail == "dpapi" and res.ok
    assert r.calls[0][-1] == "my-api-key" and r.calls[0][0].endswith("secret-exists.ps1")


def test_names_are_validated_before_anything_runs():
    r = runner_returning("STATUS found dpapi\n")
    assert bridge.exists("Bad Name", runner=r).status == "error"
    assert bridge.copy("dpapi:a-key", "env:X", runner=r).status == "error"
    assert bridge.copy("nowhere:a-key", "dpapi:b", runner=r).status == "error"
    assert bridge.remove("env:PATH", runner=r).status == "error"
    assert bridge.inject("x.env", "dotenv", {"bad key!": "dpapi:a"}, runner=r).status == "error"
    assert bridge.run_command({"1BAD": "dpapi:a"}, ["echo"], runner=r).status == "error"
    assert r.calls == []


def test_a_leaking_script_becomes_an_error_and_the_value_is_gone():
    r = runner_returning(f"STATUS stored dpapi\nthe value is {fx.fake_jwt()}\n")
    res = bridge.copy("dpapi:a-key", "credman:a-key", runner=r)
    assert res.status == "error" and "eyJ" not in res.detail and not res.lines


def test_missing_and_invalid_are_not_errors():
    assert bridge.exists("absent-key", runner=runner_returning("STATUS missing\n", code=0)).status == "missing"
    res = bridge.test("gh-token", "github", runner=runner_returning("STATUS invalid 401\n", code=1))
    assert res.status == "invalid" and res.detail == "401" and not res.ok


def test_test_builds_the_url_from_config_never_from_the_caller():
    r = runner_returning("STATUS valid 200\n")
    res = bridge.test("gh-token", "github", runner=r)
    assert res.status == "valid"
    argv = r.calls[0]
    assert "-Url" in argv and argv[argv.index("-Url") + 1].startswith("https://api.github.com/")
    assert bridge.test("gh-token", "not-configured", runner=r).status == "error"
    assert bridge.test("ado-pat", "azure-devops", runner=r).status == "error"  # needs --param org
    res = bridge.test("ado-pat", "azure-devops", {"org": "my-org"}, runner=r)
    assert res.status == "valid" and "dev.azure.com/my-org/" in r.calls[-1][r.calls[-1].index("-Url") + 1]
    assert bridge.test("ado-pat", "azure-devops", {"org": "my org; rm"}, runner=r).status == "error"


def test_inject_and_sweep_argv_shapes():
    r = runner_returning("STATUS stored C:/r/.env keys=2\n")
    res = bridge.inject("C:/r/.env", "dotenv", {"API_KEY": "dpapi:api-key", "DB_PASSWORD": "credman:db-pass"}, runner=r)
    assert res.ok and "-Map" in r.calls[0] and "API_KEY=dpapi:api-key" in r.calls[0]
    r = runner_returning("would-sweep C:/r/.env keys=API_KEY\nSTATUS listed 1\n")
    res = bridge.sweep(dry_run=True, runner=r)
    assert res.status == "listed" and res.lines == ("would-sweep C:/r/.env keys=API_KEY",) and "-WhatIf" in r.calls[0]
    assert bridge.sweep(sink_id="nothex", runner=r).status == "error"


def test_prompt_goes_through_the_console_spawner():
    r = runner_returning("STATUS opened secret my-key\n")
    res = bridge.prompt("my-key", "credman", description="GitHub PAT", runner=r)
    assert res.status == "opened"
    argv = r.calls[0]
    assert (
        argv[0].endswith("Start-CourierConsole.ps1")
        and "-ScriptPath" in argv
        and argv[argv.index("-ScriptPath") + 1].endswith("secret-prompt.ps1")
    )
    assert bridge.prompt("my-key", "env", runner=r).status == "error"
    assert bridge.prompt("my-key", "dpapi", description="x'y", runner=r).status == "error"


def test_cli_routes_and_exit_codes(monkeypatch, capsys):
    monkeypatch.setattr(bridge, "exists", lambda name, runner=None: bridge.Result("exists", "found", "credman"))
    assert cli.main(["exists", "my-key"]) == 0
    assert capsys.readouterr().out.strip() == "found credman"
    monkeypatch.setattr(bridge, "exists", lambda name, runner=None: bridge.Result("exists", "missing", ""))
    assert cli.main(["exists", "my-key"]) == 1
    monkeypatch.setattr(
        bridge, "copy", lambda s, d, replace=False, runner=None: bridge.Result("copy", "error", "refused")
    )
    assert cli.main(["copy", "dpapi:a", "env:B"]) == 2
    monkeypatch.setattr(bridge, "run_command", lambda env, cmd, runner=None: bridge.Result("run", "exit", "0"))
    assert cli.main(["run", "--env", "API_KEY=dpapi:a", "--", "npm", "start"]) == 0


def test_doctor_probes_on_this_checkout():
    assert doctor.probe_hooks().state == "OK", doctor.probe_hooks().detail
    assert doctor.probe_policy().state == "OK"
    assert doctor.probe_python().state == "OK"
    import sys

    if sys.platform == "win32":
        assert doctor.probe_fail_closed().state == "OK", doctor.probe_fail_closed().detail

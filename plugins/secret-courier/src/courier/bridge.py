"""The bridge between the model (names) and the PowerShell ops (values).

Every op is a fixed script under ``powershell/ops`` run with name-only arguments; the script prints exactly one
``STATUS <status> <detail>`` line and never a value. The bridge validates every argument as a name or a
``store:name`` before anything runs, redacts the script's output anyway, and turns a leak into an error, so a
buggy script cannot leak through it. Refusals come back as a status, never as an exception whose text could echo
an argument.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courier.paths import config_file, plugin_root
from courier.scan import redact

STORES = ("dpapi", "credman", "env", "keyvault")
WRITABLE = ("dpapi", "credman")
STATUSES = ("found", "missing", "valid", "invalid", "stored", "removed", "swept", "listed", "opened", "exit", "error")
OK_STATUSES = ("found", "valid", "stored", "removed", "swept", "listed", "opened")
_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,80}$")
_KV_NAME = re.compile(r"^[A-Za-z0-9-]{3,24}/[A-Za-z0-9-]{1,127}$")
_KEY = re.compile(r"^[A-Za-z_][\w:.-]{0,120}$")
_ENV_VAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,120}$")

Runner = Callable[[list[str], bool], tuple[str, str, int]]


@dataclass(frozen=True)
class Result:
    op: str
    status: str
    detail: str
    lines: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in OK_STATUSES or (self.status == "exit" and self.detail == "0")

    def as_dict(self) -> dict[str, Any]:
        return {"op": self.op, "status": self.status, "detail": self.detail, "lines": list(self.lines)}


class Refused(ValueError):
    """An argument the bridge will not pass on. The message names the position, never the text."""


def ops_dir() -> Path:
    return plugin_root() / "powershell" / "ops"


def console_script() -> Path:
    return plugin_root() / "powershell" / "Start-CourierConsole.ps1"


def check_name(value: str, what: str) -> str:
    if not _NAME.fullmatch(value or ""):
        raise Refused(f"{what} is not a secret name (2-81 chars: lowercase letters, digits, '-', '_', '.')")
    return value


def check_spec(value: str, what: str, destination: bool = False) -> tuple[str, str]:
    store, _, name = (value or "").partition(":")
    if store not in STORES or not name:
        raise Refused(f"{what} must be <store>:<name> with store one of {', '.join(STORES)}")
    if destination and store not in WRITABLE:
        raise Refused(
            f"{what}: {store} is never a destination (an environment variable or a vault would be readable later)"
        )
    if store == "keyvault":
        if not _KV_NAME.fullmatch(name):
            raise Refused(f"{what}: a keyvault name is <vault>/<secret>")
    elif store == "env":
        if not _ENV_VAR.fullmatch(name):
            raise Refused(f"{what}: not an environment variable name")
    else:
        check_name(name, what)
    return store, name


def _default_runner(argv: list[str], capture: bool) -> tuple[str, str, int]:
    r = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", *argv],
        capture_output=capture,
        text=True,
        timeout=600,
        check=False,
    )
    return (r.stdout or "") if capture else "", (r.stderr or "") if capture else "", r.returncode


def _parse(op: str, stdout: str, stderr: str, code: int) -> Result:
    out, leaked_out = redact(stdout)
    err, leaked_err = redact(stderr)
    lines = [ln.rstrip() for ln in out.splitlines() if ln.strip()]
    status_line = next((ln for ln in reversed(lines) if ln.startswith("STATUS ")), "")
    body = tuple(ln for ln in lines if not ln.startswith("STATUS "))
    parts = status_line.split(" ", 2)
    status = parts[1] if len(parts) > 1 else ""
    detail = parts[2] if len(parts) > 2 else ""
    if leaked_out or leaked_err:
        return Result(op, "error", "the script printed something that looks like a secret; output suppressed")
    if status not in STATUSES or status == "error" or (code != 0 and status not in ("missing", "invalid", "exit")):
        return Result(op, "error", (detail or err.strip() or f"exit {code}")[:300])
    return Result(op, status, detail[:300], body)


def _run(op: str, script: str, args: list[str], runner: Runner | None, capture: bool = True) -> Result:
    path = ops_dir() / f"{script}.ps1"
    if not path.is_file():
        return Result(op, "error", f"ops script missing: {script}.ps1")
    stdout, stderr, code = (runner or _default_runner)([str(path), *args], capture)
    if not capture:
        return Result(op, "exit", str(code))
    return _parse(op, stdout, stderr, code)


def load_endpoints() -> dict[str, dict[str, Any]]:
    """Shipped endpoints plus the developer's ``config.json`` ``endpoints`` (adds or overrides by id)."""
    base: dict[str, dict[str, Any]] = {}
    for path in (plugin_root() / "config" / "endpoints.json", config_file()):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        eps = data.get("endpoints") if isinstance(data, dict) else None
        if isinstance(eps, dict):
            base.update({k: v for k, v in eps.items() if isinstance(v, dict) and v.get("url")})
    return base


def _guard(op: str, fn: Callable[[], Result]) -> Result:
    try:
        return fn()
    except Refused as exc:
        return Result(op, "error", str(exc))


def exists(name: str, runner: Runner | None = None) -> Result:
    return _guard("exists", lambda: _run("exists", "secret-exists", [check_name(name, "name")], runner))


def names(runner: Runner | None = None) -> Result:
    return _run("names", "secret-names", [], runner)


def copy(source: str, dest: str, replace: bool = False, runner: Runner | None = None) -> Result:
    def go() -> Result:
        check_spec(source, "source")
        check_spec(dest, "destination", destination=True)
        return _run("copy", "secret-copy", [source, dest] + (["-Replace"] if replace else []), runner)

    return _guard("copy", go)


def remove(spec: str, runner: Runner | None = None) -> Result:
    def go() -> Result:
        check_spec(spec, "spec", destination=True)
        return _run("remove", "secret-remove", [spec], runner)

    return _guard("remove", go)


def prompt(
    name: str,
    store: str = "dpapi",
    description: str = "",
    source: str = "",
    replace: bool = False,
    runner: Runner | None = None,
) -> Result:
    """Open a console with the masked prompt; returns at once (``opened``)."""

    def go() -> Result:
        check_name(name, "name")
        if store not in WRITABLE:
            raise Refused("store must be dpapi or credman")
        for text, what in ((description, "description"), (source, "source")):
            if re.search(r"[\"'\r\n]", text or ""):
                raise Refused(f"{what} may not contain quotes or newlines")
        args = [name, store]
        if description:
            args += ["-Description", description]
        if source:
            args += ["-Source", source]
        if replace:
            args.append("-Replace")
        script = str(ops_dir() / "secret-prompt.ps1")
        argv = [str(console_script()), "-Title", f"secret {name}", "-ScriptPath", script, "-Arguments", *args]
        stdout, stderr, code = (runner or _default_runner)(argv, True)
        return _parse("prompt", stdout, stderr, code)

    return _guard("prompt", go)


def test(name: str, endpoint: str, params: dict[str, str] | None = None, runner: Runner | None = None) -> Result:
    def go() -> Result:
        check_name(name, "name")
        eps = load_endpoints()
        ep = eps.get(endpoint)
        if ep is None:
            raise Refused(f"endpoint id not configured (known: {', '.join(sorted(eps)) or 'none'})")
        url = str(ep["url"])
        for key in ep.get("needs", []):
            val = (params or {}).get(key)
            if not val or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", val):
                raise Refused(f"endpoint needs --param {key}=<value> (letters, digits, '.', '_', '-')")
            url = url.replace("{" + key + "}", val)
        if "{" in url:
            raise Refused("endpoint url still has an unfilled placeholder")
        args = [
            name,
            "-Url",
            url,
            "-Auth",
            str(ep.get("auth") or "bearer"),
            "-Expect",
            str(int(ep.get("expect") or 200)),
        ]
        for k, v in (ep.get("headers") or {}).items():
            args += ["-Header", f"{k}={v}"]
        return _run("test", "secret-test", args, runner)

    return _guard("test", go)


def inject(
    target: str, fmt: str, mapping: dict[str, str], replace: bool = False, runner: Runner | None = None
) -> Result:
    def go() -> Result:
        if fmt not in ("dotenv", "json", "user-secrets"):
            raise Refused("format must be dotenv, json or user-secrets")
        if not target or re.search(r"[\"'\r\n]", target):
            raise Refused("target path may not contain quotes or newlines")
        pairs: list[str] = []
        for key, spec in mapping.items():
            if not _KEY.fullmatch(key):
                raise Refused("a target key must be a setting name (letters, digits, ':', '.', '_', '-')")
            check_spec(spec, f"source for {key}")
            pairs.append(f"{key}={spec}")
        if not pairs:
            raise Refused("nothing to inject")
        args = ["-Target", target, "-Format", fmt, "-Map", *pairs] + (["-Replace"] if replace else [])
        return _run("inject", "secret-inject", args, runner)

    return _guard("inject", go)


def sinks(repo: str = "", runner: Runner | None = None) -> Result:
    def go() -> Result:
        if repo and not re.fullmatch(r"[\w.\\/: -]{1,200}", repo):
            raise Refused("repo filter has unexpected characters")
        return _run("sinks", "secret-sinks", ["-Repo", repo] if repo else [], runner)

    return _guard("sinks", go)


def sweep(
    sink_id: str = "",
    older_days: int | None = None,
    repo: str = "",
    dry_run: bool = False,
    runner: Runner | None = None,
) -> Result:
    def go() -> Result:
        args: list[str] = []
        if sink_id:
            if not re.fullmatch(r"[0-9a-f]{12}", sink_id):
                raise Refused("sink id is 12 hex characters (see `courier sinks`)")
            args += ["-Id", sink_id]
        if older_days is not None:
            args += ["-OlderDays", str(int(older_days))]
        if repo:
            args += ["-Repo", repo]
        if dry_run:
            args.append("-WhatIf")
        return _run("sweep", "secret-sweep", args, runner)

    return _guard("sweep", go)


def run_command(env_map: dict[str, str], command: list[str], runner: Runner | None = None) -> Result:
    """Run ``command`` with the named values in its environment only; the child inherits the console."""

    def go() -> Result:
        if not command:
            raise Refused("nothing to run")
        for var, spec in env_map.items():
            if not _ENV_VAR.fullmatch(var):
                raise Refused("an environment variable name is letters, digits and '_'")
            check_spec(spec, f"source for {var}")
        if not env_map:
            raise Refused("no --env VAR=<store>:<name> given")
        # both specs travel base64-encoded so the child's own flags never bind to the script's parameters
        env_b64 = base64.b64encode(json.dumps(env_map).encode("utf-8")).decode("ascii")
        cmd_b64 = base64.b64encode(json.dumps(list(command)).encode("utf-8")).decode("ascii")
        return _run("run", "secret-run", ["-EnvSpec", env_b64, "-CommandSpec", cmd_b64], runner, capture=False)

    return _guard("run", go)


__all__ = [
    "OK_STATUSES",
    "STATUSES",
    "STORES",
    "Refused",
    "Result",
    "Runner",
    "check_name",
    "check_spec",
    "copy",
    "exists",
    "inject",
    "load_endpoints",
    "names",
    "prompt",
    "remove",
    "run_command",
    "sinks",
    "sweep",
    "test",
]

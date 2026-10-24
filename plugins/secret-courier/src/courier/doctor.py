"""``courier doctor``: is the plugin wired and fail-closed on this machine? Each probe names one fix."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from courier import __version__
from courier.paths import home, plugin_root
from courier.policy import POLICY

OK, WARN, FAIL = "OK", "WARN", "FAIL"


@dataclass(frozen=True)
class Probe:
    name: str
    state: str
    detail: str
    fix: str = ""

    def line(self) -> str:
        tail = f" -> {self.fix}" if self.fix and self.state != OK else ""
        return f"[{self.state}] {self.name} - {self.detail}{tail}"


def probe_python() -> Probe:
    v = sys.version_info
    if v < (3, 11):
        return Probe(
            "python",
            FAIL,
            f"{v.major}.{v.minor} is too old",
            "install Python 3.11+ (winget install Python.Python.3.13)",
        )
    return Probe("python", OK, f"{v.major}.{v.minor}.{v.micro}, secret-courier {__version__}")


def probe_pwsh() -> Probe:
    exe = shutil.which("pwsh")
    if not exe:
        return Probe(
            "pwsh", FAIL, "PowerShell 7 is not on PATH; every op needs it", "winget install Microsoft.PowerShell"
        )
    return Probe("pwsh", OK, exe)


def hook_command_line(hook: dict) -> str:
    """The command a hook runs, in shell form or exec form (command plus args)."""
    return " ".join([hook.get("command", ""), *hook.get("args", [])])


def probe_hooks(root: Path | None = None) -> Probe:
    root = root or plugin_root()
    path = root / "hooks" / "hooks.json"
    try:
        hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
    except (OSError, ValueError, KeyError) as exc:
        return Probe("hooks", FAIL, f"hooks.json: {exc.__class__.__name__}", "restore hooks/hooks.json from git")
    problems: list[str] = []
    for name in ("courier-guard.cmd", "courier_entry.py"):
        if not (root / "scripts" / name).exists():
            problems.append(f"scripts/{name} is missing")
    guards = [
        h
        for e in hooks.get("PreToolUse", [])
        for h in e.get("hooks", [])
        if "courier-guard.cmd" in hook_command_line(h)
    ]
    matchers = {m for e in hooks.get("PreToolUse", []) for m in e.get("matcher", "").split("|")}
    for tool in ("Bash", "PowerShell", "Read", "Grep", "Glob", "Write", "Edit", "NotebookEdit"):
        if tool not in matchers:
            problems.append(f"no PreToolUse guard for {tool}")
    if any(h.get("onFailure") != "block" for h in guards):
        problems.append('a guard lacks "onFailure": "block"')
    if not any(
        "--prompt-hook" in hook_command_line(h) for e in hooks.get("UserPromptSubmit", []) for h in e.get("hooks", [])
    ):
        problems.append("no UserPromptSubmit paste hook")
    if problems:
        return Probe("hooks", FAIL, "; ".join(problems), "restore hooks/hooks.json and scripts/ from git")
    return Probe(
        "hooks", OK, f"{len(guards)} tool guards block on failure, paste hook wired, paste policy {POLICY.paste}"
    )


def probe_fail_closed(root: Path | None = None) -> Probe:
    """A copy of the wrapper with no interpreter on PATH exits 2: the tool call is refused, never let through."""
    root = root or plugin_root()
    name = "guard fail-closed"
    if sys.platform != "win32":
        return Probe(name, OK, "not a Windows host; the cmd wrapper is not exercised")
    wrapper = root / "scripts" / "courier-guard.cmd"
    if not wrapper.exists():
        return Probe(name, FAIL, "scripts/courier-guard.cmd is missing", "restore scripts/ from git")
    with tempfile.TemporaryDirectory() as tmp:
        scripts = Path(tmp) / "plugin" / "scripts"
        scripts.mkdir(parents=True)
        shutil.copyfile(wrapper, scripts / "courier-guard.cmd")
        env = {k: v for k, v in os.environ.items() if k != "COURIER_PYTHON"}
        env["PATH"] = str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32")
        try:
            proc = subprocess.run(
                ["cmd", "/c", str(scripts / "courier-guard.cmd"), "--bash-hook"],
                input='{"tool_input":{"command":"echo hi"}}',
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return Probe(
                name,
                FAIL,
                f"could not run the wrapper: {exc.__class__.__name__}",
                "restore scripts/courier-guard.cmd from git",
            )
    if proc.returncode == 2:
        return Probe(name, OK, "no interpreter -> exit 2, the tool call is refused")
    return Probe(
        name,
        FAIL,
        f"the wrapper exited {proc.returncode} with no interpreter",
        "restore scripts/courier-guard.cmd from git",
    )


def probe_policy() -> Probe:
    if POLICY.overlay_problems:
        return Probe(
            "policy",
            WARN,
            "overlay ignored in part: " + "; ".join(POLICY.overlay_problems),
            "fix ~/.secret-courier/guard-policy.json",
        )
    return Probe(
        "policy",
        OK,
        f"{len(POLICY.denied_file_families)} file families, {len(POLICY.value_dump_tokens)} value-dump tokens, "
        f"paste {POLICY.paste}",
    )


def probe_home() -> Probe:
    h = home()
    if not h.exists():
        return Probe("home", OK, f"{h} not created yet (the first `courier prompt` creates it with an owner-only ACL)")
    if sys.platform == "win32":
        try:
            out = subprocess.run(["icacls", str(h)], capture_output=True, text=True, timeout=30, check=False).stdout
        except (OSError, subprocess.TimeoutExpired):
            out = ""
        others = [
            ln
            for ln in out.splitlines()[1:]
            if ln.strip()
            and not any(
                k in ln for k in ("NT AUTHORITY\\SYSTEM", "BUILTIN\\Administrators", os.environ.get("USERNAME", "\0"))
            )
        ]
        others = [ln for ln in others if "Successfully processed" not in ln]
        if others:
            return Probe(
                "home",
                WARN,
                f"{h} grants access beyond the owner",
                "run any `courier prompt`/`courier copy` (re-applies the ACL)",
            )
    return Probe("home", OK, str(h))


def _module_logging_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging"
        ) as k:
            value, _kind = winreg.QueryValueEx(k, "EnableModuleLogging")
        return int(value) == 1
    except (OSError, ValueError, TypeError):
        return False


def probe_ps_logging() -> Probe:
    if _module_logging_enabled():
        return Probe(
            "ps logging",
            WARN,
            "host policy logs PowerShell cmdlet parameter values; the ops keep values in SecureString and .NET "
            "calls by rule (SECURITY.md)",
        )
    return Probe("ps logging", OK, "module logging off or not a Windows host")


def probes() -> list[Probe]:
    return [
        probe_python(),
        probe_pwsh(),
        probe_hooks(),
        probe_fail_closed(),
        probe_policy(),
        probe_home(),
        probe_ps_logging(),
    ]


def main(as_json: bool = False) -> int:
    results = probes()
    if as_json:
        print(json.dumps([p.__dict__ for p in results], indent=2))
    else:
        for p in results:
            print(p.line())
        failed = [p for p in results if p.state == FAIL]
        print("Healthy" if not failed else f"Next: {failed[0].fix or failed[0].detail}")
    return 1 if any(p.state == FAIL for p in results) else 0


__all__ = [
    "FAIL",
    "OK",
    "WARN",
    "Probe",
    "main",
    "probe_fail_closed",
    "probe_hooks",
    "probe_policy",
    "probe_ps_logging",
    "probes",
]

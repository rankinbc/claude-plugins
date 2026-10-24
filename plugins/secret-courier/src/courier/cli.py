"""``courier`` CLI: names in, one status line out. Exit 0 on success, 1 when the thing is missing or invalid,
2 on a refusal or an error. Never prints a value (the bridge redacts the ops' output anyway)."""

from __future__ import annotations

import argparse
import sys

from courier import __version__, bridge


def _kv(items: list[str] | None, what: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise SystemExit(f"{what} entries are KEY=value")
        out[key] = value
    return out


def _report(result: bridge.Result) -> int:
    for line in result.lines:
        print(line)
    print(f"{result.status} {result.detail}".rstrip())
    if result.status == "error":
        return 2
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="courier", description="Move secrets by NAME; the value never passes through Claude."
    )
    p.add_argument("--version", action="version", version=f"secret-courier {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("exists", help="which store holds NAME (dpapi, credman, env)")
    s.add_argument("name")
    sub.add_parser("names", help="every name the store or the manifest knows, with where it is held")
    s = sub.add_parser("prompt", help="open a console with a masked prompt and store what is typed")
    s.add_argument("name")
    s.add_argument("--store", default="dpapi", choices=["dpapi", "credman"])
    s.add_argument("--description", default="")
    s.add_argument("--source", default="", help="where a teammate can obtain it (vault, team, portal)")
    s.add_argument("--replace", action="store_true")
    s = sub.add_parser("copy", help="copy <store>:<name> to <store>:<name> (env and keyvault are sources only)")
    s.add_argument("source")
    s.add_argument("dest")
    s.add_argument("--replace", action="store_true")
    s = sub.add_parser("remove", help="remove <store>:<name>")
    s.add_argument("spec")
    s = sub.add_parser("test", help="probe a configured endpoint id with NAME (config/endpoints.json)")
    s.add_argument("name")
    s.add_argument("endpoint")
    s.add_argument("--param", action="append", help="KEY=value for an endpoint placeholder such as {org}")
    s = sub.add_parser("inject", help="write named values into a consumer's local config (a ledgered sink)")
    s.add_argument("--target", required=True, help="file path, or a .csproj / UserSecretsId for user-secrets")
    s.add_argument("--format", required=True, choices=["dotenv", "json", "user-secrets"])
    s.add_argument("--map", action="append", required=True, help="KEY=<store>:<name>")
    s.add_argument("--replace", action="store_true")
    s = sub.add_parser("run", help="run a command with named values in ITS environment only")
    s.add_argument("--env", action="append", required=True, help="VAR=<store>:<name>")
    s.add_argument("command", nargs=argparse.REMAINDER)
    s = sub.add_parser("sinks", help="list the plaintext copies this plugin wrote (the ledger)")
    s.add_argument("--repo", default="")
    s = sub.add_parser("sweep", help="remove ledgered plaintext copies")
    s.add_argument("--id", default="")
    s.add_argument("--older-days", type=int)
    s.add_argument("--repo", default="")
    s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("scan", help="scan files or folders for secret-shaped values (never prints one)")
    s.add_argument("paths", nargs="+")
    s.add_argument("--fail-on-findings", action="store_true")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("doctor", help="is the plugin wired and fail-closed on this machine?")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("log", help="what the plugin did and when (the audit log; names only)")
    s.add_argument("-n", type=int, default=20, help="last N entries (default 20)")
    return p


def _log(n: int) -> int:
    import json

    from courier.paths import audit_file
    from courier.scan import sanitize_text

    path = audit_file()
    if not path.exists():
        print("no audit log yet: nothing has run")
        return 0
    entries = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(n, 1) :]
    for raw in entries:
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        # the audit log records names/statuses only, but redact the detail defensively so `courier log` can
        # never surface a value even if a future op logged one by mistake (finding 10).
        detail = sanitize_text(str(e.get("detail", "")))
        print(f"{e.get('ts', '')}  {e.get('op', ''):<8} {e.get('status', ''):<8} {detail}")
    print(f"{len(entries)} entries from {path} (names and statuses only; values are never logged)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "exists":
        return _report(bridge.exists(args.name))
    if args.cmd == "names":
        return _report(bridge.names())
    if args.cmd == "prompt":
        return _report(bridge.prompt(args.name, args.store, args.description, args.source, args.replace))
    if args.cmd == "copy":
        return _report(bridge.copy(args.source, args.dest, args.replace))
    if args.cmd == "remove":
        return _report(bridge.remove(args.spec))
    if args.cmd == "test":
        return _report(bridge.test(args.name, args.endpoint, _kv(args.param, "--param")))
    if args.cmd == "inject":
        return _report(bridge.inject(args.target, args.format, _kv(args.map, "--map"), args.replace))
    if args.cmd == "run":
        command = [c for c in args.command if c != "--"]
        return _report(bridge.run_command(_kv(args.env, "--env"), command))
    if args.cmd == "sinks":
        return _report(bridge.sinks(args.repo))
    if args.cmd == "sweep":
        return _report(bridge.sweep(args.id, args.older_days, args.repo, args.dry_run))
    if args.cmd == "log":
        return _log(args.n)
    if args.cmd == "scan":
        from courier.scan import main as scan_main

        return scan_main(
            args.paths + (["--fail-on-findings"] if args.fail_on_findings else []) + (["--json"] if args.json else [])
        )
    if args.cmd == "doctor":
        from courier.doctor import main as doctor_main

        return doctor_main(args.json)
    return 2


if __name__ == "__main__":
    sys.exit(main())

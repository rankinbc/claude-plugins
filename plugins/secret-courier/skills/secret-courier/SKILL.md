---
name: secret-courier
description: Use whenever a task needs a secret value (API key, token, password, connection string, certificate password) to exist somewhere - in a local config file, in a process environment, in Windows Credential Manager - or when the developer pastes or is about to paste one. Moves secrets by NAME so Claude never sees a value; records every plaintext copy it makes so it can be swept.
---

# secret-courier

Claude handles secret NAMES and locations. The ops scripts move VALUES. Full contract: `SECURITY.md` at the
plugin root.

The CLI is `scripts\courier.cmd` under the plugin root. Installed from the marketplace that root is
`%USERPROFILE%\.claude\plugins\cache\secret-courier\secret-courier\<version>`; from a checkout it is the repo
folder. Run it through the Bash tool as `"<plugin root>/scripts/courier.cmd" <command> ...`. Every command
prints a plain sentence saying what happened to the value and where it is now, then one status line (`found
dpapi`, `missing`, `stored credman`, `error ...`), and never a value. **Relay that sentence to the developer**
in your own words or verbatim; it is how they know the operation was safe. `courier log` shows what the plugin
did and when.

## Decide the path

| Situation | Do this |
|---|---|
| A tool, script or app needs a secret the developer has | `courier exists <name>` -> `missing`: `courier prompt <name> --description "<what it is for>" --source "<where it comes from>"`. A console opens with a masked prompt; tell the developer to type or paste the value THERE, then continue with the name. |
| A repo needs the value in its local config (`.env`, `appsettings.local.json`, dotnet user-secrets) | `courier inject --target <file or .csproj> --format dotenv\|json\|user-secrets --map KEY=dpapi:<name>`. Refuses a file git would not ignore. The copy is recorded in the ledger. |
| A command needs the value only while it runs | `courier run --env VAR=dpapi:<name> -- <command> <args>`. The value exists only in that child process. Prefer this over `inject`. |
| Is this token still valid? | `courier test <name> <endpoint-id>` (ids in `config/endpoints.json`; `--param org=<x>` fills `{org}`). Reports `valid 200` / `invalid 401`. |
| Move a secret between stores | `courier copy dpapi:<name> credman:<name>` (`env:` and `keyvault:` are sources only; an existing destination needs `--replace`). |
| What plaintext copies exist, and clean up | `courier sinks`, then `courier sweep [--id <id> \| --older-days <n> \| --repo <name>] [--dry-run]`. Offer a sweep at the end of any task that injected. |
| The developer pastes a secret into chat | Stop. One short paragraph on why it must not be in the transcript. Run `courier prompt <name>` so they enter it in the console. Do not use, repeat or store the pasted value. Suggest they rotate it if it was a real one. |
| Something refuses to run (`Blocked: ...`) | The guard hook refused a read, a write or a command that would expose a value. Do not work around it; use the commands above. |
| Is the plugin healthy? | `courier doctor` - every probe names one fix. |

## Never

- Ask the developer to paste a value into chat, a command line, a file Claude writes, or an environment variable
  Claude exports.
- Read `.env*`, `secrets.json`, `appsettings.local.json`, `local.settings.json`, key or certificate files,
  `~/.secret-courier`, `~/.ssh`, `~/.aws`, `~/.azure`, `~/.kube` (the hooks refuse; do not try another route).
- Print, log or echo a value; run anything that would (`printenv`, `Get-ChildItem env:`,
  `ConvertFrom-SecureString`, `keyring get`, `az keyvault secret show`, `aws secretsmanager get-secret-value` ...).
- Write a script that reads a value and prints it, then run it: the write hook refuses the first step and the
  bash hook scans the script on the second.

## Names

Lowercase letters, digits, `-`, `_`, `.`; 2 to 81 characters (`github-pat`, `db.password.dev`). Stores:
`dpapi` (encrypted file under `~/.secret-courier`, the default), `credman` (Windows Credential Manager),
`env` (read-only source), `keyvault:<vault>/<secret>` (read-only, interactive, under the developer's own
`az login`).

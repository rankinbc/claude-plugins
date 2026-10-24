# SECURITY.md - the contract

secret-courier exists so that a secret can be useful to an AI coding session without the model ever holding the
value. Three rules, enforced in code, not by convention.

## 1. Names and locations are the model's; values are the scripts'

Every operation takes `<store>:<name>` arguments, validated as names before anything runs
(`src/courier/bridge.py`). Every op (`powershell/ops/*.ps1`) prints exactly one `STATUS <status> <detail>`
line and never a value. The bridge redacts the op's output anyway and turns anything secret-shaped into an
error, so a buggy script cannot leak through it. A value enters the system in one of three ways only:

- typed at a masked prompt in a console the plugin opens (`courier prompt`): `Read-Host -AsSecureString`, the
  clipboard cleared afterwards if it still holds the value;
- imported from a store the developer already has (`env:` or `keyvault:` as a source of `courier copy`);
- read from a store the plugin wrote earlier.

Inside the scripts a value travels as `SecureString`. No value is passed to a PowerShell cmdlet as a
parameter (host module logging, where policy enables it, records those): file writes use `[IO.File]`,
HTTP probes use `HttpClient`, Credential Manager uses P/Invoke, and the only plaintext is the string a .NET
call needs for the moment it needs it.

## 2. Every place a value may exist is enumerable

| Kind | Where | Protection | Enumerated by |
|---|---|---|---|
| store `dpapi` | `~/.secret-courier/secrets.json` | DPAPI for the current Windows user; owner-only ACL (explicit ACEs stripped, including the logon-session SID) | `courier names` |
| store `credman` | Windows Credential Manager `secret-courier/<name>` | the OS credential vault, current user | `courier names` |
| sink | a `.env`, `appsettings.local.json`, dotnet user-secrets file the plugin wrote with `courier inject` | plaintext by necessity: refused unless git ignores the file, owner-only ACL, recorded in `~/.secret-courier/sinks.json` (path, keys, time; never values) | `courier sinks`; removed by `courier sweep` |
| transit | the environment of one child process (`courier run`) | nothing is written anywhere | nothing to clean |

`~/.secret-courier` also holds `secrets.manifest.json` (name, description, source, store) and `audit.jsonl`
(one line per op: time, op, status, detail; names only). Both are safe for the model to read and are listed in
the policy's `allowed_files`.

Sources that are never destinations: `env:` (an exported variable would be readable by any later command) and
`keyvault:` (a network read under the developer's own `az login`, interactive only).

## 3. The guard is a boundary, not a courtesy

`hooks/hooks.json` runs `scripts/courier-guard.cmd` before every `Bash`, `PowerShell`, `Read`, `Grep`, `Glob`,
`Write`, `Edit` and `NotebookEdit` call, and on every prompt. The guard is stdlib-only Python 3.11+ with no
venv: the wrapper finds an interpreter (`COURIER_PYTHON`, `py -3`, `python`, `python3`) and runs
`scripts/courier_entry.py`. It fails closed: no interpreter, an import error, a non-zero exit, a timeout or a
hook that cannot start all refuse the tool call (`"onFailure": "block"`, Claude Code 2.1.295+). The prompt hook
alone fails open so a developer's message is never lost.

What it refuses (`config/guard-policy.json`; a developer overlay at `~/.secret-courier/guard-policy.json` may
only add entries and set `paste`):

- reading, grepping, globbing, writing or editing a secret-bearing file family (`.env*`, `secrets.json`,
  `appsettings.local.json`, `local.settings.json`, key and certificate files, `.netrc`, `.pgpass`,
  `terraform.tfvars`, `~/.ssh`, `~/.aws`, `~/.azure`, `~/.kube`, `~/.secret-courier` ...), including backup
  copies, 8.3 short names, symlinks and `*.{pem,key}` brace globs;
- a command that prints or decrypts values: environment dumps in any interpreter, `ConvertFrom-SecureString`,
  `keyring get`, `cmdkey`, `az keyvault secret show`, `az ... keys list`, `aws secretsmanager get-secret-value`,
  `gcloud secrets versions access`, `vault kv get`, `op read`, `gh auth token`, `kubectl get secret -o ...`,
  references to credential-named variables (`$env:GITHUB_TOKEN`), git config and remote dumps, encoded
  PowerShell commands however nested;
- a secret-shaped value in a command, a file being written, or a prompt (`paste: advise` injects the
  interceptor instruction; `paste: block` refuses the message);
- a script the command runs that would do any of the above (`pwsh -File temp.ps1`, `python x.py`), a nested
  shell (`bash -c`, `pwsh -Command`, `cmd /c`), a glob that reaches a secret family, and a pipe or command
  substitution fed by a listing of a secret file.

## Guard limits (read before relying on it)

- A text check cannot see a path or token assembled inside an interpreter (`'.e'+'nv'`). The Read/Write
  hooks and the OS ACL on the store are the floor beneath the Bash guard; the Bash guard is a guardrail against
  the obvious, not a boundary against a determined command.
- A blocked prompt still lands in the Claude Code session transcript on disk; `block` is a context control, not
  a disk control.
- DPAPI for the current user protects against other users and offline theft, not against code running as you.
  The plugin's own ops run as you; so does anything else you run.
- Where host policy turns on PowerShell module logging (`courier doctor` warns `ps logging`), the host records
  cmdlet parameter values in the operational event log. The rule in section 1 is the only defence.
- Hooks apply to Claude Code's own tools. A third-party MCP server that reads files is not covered.
- Windows only in this version (DPAPI, Credential Manager, the `.cmd` wrappers).

## Reporting

Open an issue on the repository. Do not include a real value in the report.

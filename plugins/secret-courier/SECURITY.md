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
| transit | the environment of one child process (`courier run`) | nothing is written anywhere; the child's stdout/stderr are captured and the injected value (and its base64/url-encoded/reversed forms) masked before any output is relayed | nothing to clean |

`~/.secret-courier` also holds `secrets.manifest.json` (name, description, source, store), `audit.jsonl`
(one line per op: time, op, status, detail; names only), `config.json` (endpoint ids and URLs; no values) and an
optional `guard-policy.json` overlay. These are value-free and the model may **read** them (anchored entries in
the policy's `allowed_files`). The model never **writes or edits** anything in `~/.secret-courier` or in the
plugin's own install directory: those are protected roots, refused by the Write/Edit/Bash-write guard regardless
of any allow list, so the guard config, hooks, ops, stores and ledger are only ever changed by a human.

Sources that are never destinations: `env:` (an exported variable would be readable by any later command) and
`keyvault:` (a network read under the developer's own `az login`, interactive only).

## 3. The guard is a boundary, not a courtesy

`hooks/hooks.json` starts `cmd.exe /d /c scripts\courier-guard.cmd` directly (exec form, no shell, so it
behaves the same with or without Git Bash) before every `Bash`, `PowerShell`, `Read`, `Grep`, `Glob`,
`Write`, `Edit` and `NotebookEdit` call, and on every prompt. The guard is stdlib-only Python 3.11+ with no
venv: the wrapper finds an interpreter (`COURIER_PYTHON`, `py -3`, `python`, `python3`) and runs
`scripts/courier_entry.py`. It fails closed: no interpreter, an import error, a non-zero exit, a timeout or a
hook that cannot start all refuse the tool call (`"onFailure": "block"`, Claude Code 2.1.295+). The prompt hook
alone fails open so a developer's message is never lost.

What it refuses (`config/guard-policy.json`; a developer overlay at `~/.secret-courier/guard-policy.json` may
only **tighten** the guard — add entries to `denied_file_families`, `denied_dirs`, `denied_samples`,
`value_dump_tokens` and set `paste`. It can never add an allow, widen a safe-list, or change anything else;
such keys are ignored and `courier doctor` reports them):

- reading, grepping, globbing, writing or editing a secret-bearing file family (`.env*`, `secrets.json`,
  `appsettings.local.json`, `local.settings.json`, key and certificate files, `.netrc`, `.pgpass`,
  `terraform.tfvars`, `~/.ssh`, `~/.aws`, `~/.azure`, `~/.kube`, `~/.secret-courier`, `.docker/config.json` ...),
  including backup copies, 8.3 short names, symlinks, `*.{pem,key}` brace globs, and an NTFS alternate-data-stream
  suffix (`.env::$DATA`). Allow-list entries are anchored (repo-relative), so a bare `config.json` allow can no
  longer shadow `.docker/config.json`, and a deny is evaluated before an allow;
- writing or editing anything inside a protected root — `~/.secret-courier` (wherever `COURIER_HOME` points) and
  the plugin's own install directory — so the guard config, hooks, ops and the stores/ledger are never the model's
  to change;
- a command that prints or decrypts values: environment dumps in any interpreter (`env`, `env -0`, `printenv`,
  `set`, `set G`, `declare -p`, `cmd /c set`), `ConvertFrom-SecureString`, the plugin's own decrypt/import APIs
  (`Get-CourierStoreValue`, `Get-CourierSecretValue`, `[CourierCred]::Read`, `Import-Module ...\Courier.psm1`,
  `NetworkCredential`, `ProtectedData::Unprotect`, `CredRead`), `keyring get`, `cmdkey`, `az keyvault secret
  show`, `az ... keys list`, `aws secretsmanager get-secret-value`, `gcloud secrets versions access`,
  `vault kv get`, `op read`, `gh auth token`, `kubectl get secret -o ...`, references to credential-named
  variables case-insensitively and in any shell (`$env:GITHUB_TOKEN`, `$env:openai_key`, `process.env.GITHUB_TOKEN`,
  `getenv('github_token')`), git config and remote dumps, encoded PowerShell commands however nested;
- a recursive content search over an unscoped tree (`grep -r ... .`, `rg PASSWORD`, `findstr /s ... *`) and a
  content-reader globbing a whole directory (`cat *`, `Get-Content *`), which would read any secret file in it;
  a Grep tool call in `content` output mode over a directory (it returns matching lines) — allowed only against a
  single specific file;
- a secret-shaped value in a command, a file being written (including every `edits[].new_string` of a
  MultiEdit), or a prompt (`paste: advise` injects the interceptor instruction; `paste: block` refuses the
  message);
- a script the command runs or sources that would do any of the above (`pwsh -File temp.ps1`, `python x.py`,
  `python notes.txt`, `./dump.ps1`, `. ./dump.ps1`) — a script too large to scan (>256 KB) is refused, not waved
  through; a nested shell (`bash -c`, `pwsh -Command`, `cmd /c`), a glob that reaches a secret family, a
  bracket/quote-concatenated name (`.[e]nv`, `'.e''nv'`), and a pipe or command substitution fed by a listing of a
  secret file;
- a UNC or device path (`\\host\share\...`) is evaluated **lexically only** and never resolved or stat'd, so the
  guard cannot be turned into an NTLM-hash leak, while a secret-named UNC path is still denied;
- an oversized command (>256 KB) is refused with a clear message rather than scanned slowly.

`courier test` sends a named secret only to an endpoint from the shipped/`config.json` list, and only after the
substituted URL is checked to be `https` and its host to be the endpoint's declared host, so a `{param}` can
never inject a different host.

## Guard limits (read before relying on it)

- A text check cannot see a path or token assembled inside an interpreter (`'.e'+'nv'`, `f=.en; cat ${f}v`, a
  value rebuilt from pieces). The Read/Write hooks and the OS ACL on the store are the floor beneath the Bash
  guard; the Bash guard is a guardrail against the obvious, not a boundary against a determined command.
- `courier run` captures and redacts the child's output, masking each injected value and its base64, URL-encoded
  and reversed forms. A child that **transforms** the value further — hashes it, splits it across lines, encrypts
  or otherwise re-encodes it — can still emit something the mask does not match. `courier run` gives a value to a
  process; it cannot police what that process then does with it. (The child is run non-interactively, since its
  streams are captured.)
- A recursive search **scoped to a named directory** (`grep -r TODO src`) is allowed and trusted to the
  developer's scoping; it is not inspected for a secret file nested inside that directory. Only an unscoped tree
  walk (the working directory, a drive/home root, or a bare glob) is refused.
- A dotenv value containing a newline cannot be represented safely, so `courier inject --format dotenv` refuses
  it (use `json` or `user-secrets`).
- If a value is pasted into the `courier prompt` console, Windows Clipboard History (Win+V) may retain it even
  though the plugin clears the live clipboard. Turn off clipboard history, or clear it, when pasting secrets.
- A blocked prompt still lands in the Claude Code session transcript on disk; `block` is a context control, not
  a disk control.
- DPAPI for the current user protects against other users and offline theft, not against code running as you.
  The plugin's own ops run as you; so does anything else you run.
- Where host policy turns on PowerShell module logging (`courier doctor` warns `ps logging`), the host records
  cmdlet parameter values in the operational event log. The rule in section 1 is the only defence.
- Hooks apply to Claude Code's own tools. A third-party MCP server that reads files is not covered.
- Where host policy turns on PowerShell module/script-block logging, a cmdlet parameter value would be recorded.
  The ops avoid this by rule: no secret value is ever passed as a cmdlet parameter — values travel as
  `SecureString`, file writes use `[IO.File]`, HTTP uses `HttpClient`, Credential Manager uses P/Invoke, and the
  `courier run` child reads the value from its own environment, never a logged argument. `courier doctor` warns
  when module logging is on.
- Windows only in this version (DPAPI, Credential Manager, the `.cmd` wrappers). On macOS/Linux `cmd.exe` does not
  exist, so every guarded tool call is refused until the plugin is disabled there (`/plugin`). The guard is
  not a cross-platform boundary; treat a non-Windows host as unprotected.

## Reporting

Open an issue on the repository. Do not include a real value in the report.

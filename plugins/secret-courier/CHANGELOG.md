# Changelog

All notable changes to secret-courier are recorded here. The format follows Keep a Changelog; versions follow
semantic versioning.

## 0.2.0 - Unreleased

Moved into the [rankinbc/claude-plugins](https://github.com/rankinbc/claude-plugins) marketplace. Install with
`/plugin install secret-courier@rankinbc`. Releases are tagged `secret-courier--vX.Y.Z`.

### Security

- The guard's own configuration can no longer be changed by Claude: writes under `~/.secret-courier` and the
  plugin's install folder are refused whatever the allow lists say, deny rules are checked before allow
  rules, and allow entries are anchored to the courier home. The developer overlay can only tighten the policy.
- `courier test` sends a secret only over https to the endpoint's own declared host; a `{param}` cannot change
  the host.
- `courier run` captures the child's output and masks each injected value (plain, base64, URL-encoded and
  reversed) before Claude sees it.
- The command scanner refuses the plugin's own decrypt APIs (`Get-CourierStoreValue`, `CourierCred`, importing
  `Courier.psm1`, `ProtectedData::Unprotect`, ...).
- Closed shell bypasses: bracket globs (`.[e]nv`), quote splitting (`'.e''nv'`), NTFS alternate data streams,
  case-insensitive environment access, `process.env`, environment dumps (`env -0`, `declare -p`, `set G`),
  unscoped recursive searches (`grep -r`, `rg -uu`, `findstr /s`), directly executed scripts and scripts over
  256 KB (now refused).
- UNC and device paths are judged by name only and never touched, so a lookup cannot leak NTLM credentials.

### Changed

- Hooks start `cmd.exe` directly (exec form), so they behave the same with or without Git Bash.
- The SessionStart check also runs on resume, clear and compact.
- Commands over 64 KB are refused with a clear message.
- `courier log` redacts its detail column; dotenv injection refuses values that contain a newline.
- `tests/fixtures` is no longer an allow-anywhere path.
- SECURITY.md lists what the guard cannot catch.

## 0.1.0 - 2026-10-20

First release. Windows only.

- Every op prints a plain sentence saying what happened to the value and where it is now (store, encryption,
  ACL, git-ignore, ledger id and the matching `sweep` command) before its status line; the `prompt` console
  explains where the value goes and what Claude sees before you type; refusals from the hooks name the
  `courier` command to use instead; `courier log` shows the audit log (names and statuses only).
- A SessionStart line says whether the guard is live and what is missing.

- Stores: `dpapi` (DPAPI-encrypted file under `~/.secret-courier`, owner-only ACL) and `credman` (Windows
  Credential Manager); `env` and `keyvault` as read-only sources.
- Operations, each printing one `STATUS` line and never a value: `exists`, `names`, `prompt` (masked console
  prompt), `copy`, `remove`, `test` (HTTPS probe through `HttpClient`), `inject` (git-ignored, ACL'd,
  ledgered local config), `run` (value only in a child process environment), `sinks`, `sweep`, `scan`, `doctor`.
- Guard hooks for Bash, PowerShell, Read, Grep, Glob, Write, Edit, NotebookEdit and the prompt: stdlib-only
  Python, no virtual environment, fail closed on every failure path.
- Policy file `config/guard-policy.json` with an add-only developer overlay; endpoint catalogue
  `config/endpoints.json` with a developer overlay.
- Skill `secret-courier` and command `/courier`.

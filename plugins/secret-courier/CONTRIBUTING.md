# Contributing

Thanks for looking. A few things keep this plugin trustworthy; please keep them true.

## The rules the code enforces

1. The model handles names; scripts handle values. Nothing under `src/` may ever hold a secret value, and
   nothing under `powershell/` may print one. An op prints exactly one `STATUS <status> <detail>` line.
2. Inside PowerShell a value travels as `SecureString`. Never pass a value to a cmdlet as a parameter; use
   `[IO.File]`, `HttpClient`, P/Invoke, or `ConvertFrom-CourierSecureString` right before the .NET call that
   needs it, and null the variable afterwards.
3. The guard chain (`src/courier/guard*.py`, `policy.py`, `patterns.py`, `scan.py`) stays standard-library
   only. `tests/test_entry_and_policy.py::test_guard_chain_is_stdlib_only` enforces it.
4. Deny lists live in `config/guard-policy.json`, not in code.
5. No secret-shaped string may live in the repo: build fixtures at runtime (`tests/fixtures.py`) and mark a
   test module with `courier-scan: ignore-file`. CI runs `courier scan . --fail-on-findings`.

## Working on it

```
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts && python -m ruff format src tests scripts
python -m pytest -q
pwsh -NoProfile -Command "Invoke-Pester -Path powershell/tests"
```

PowerShell files are CRLF (`.gitattributes`); Python files are LF. Tests never make a live cloud call: the
Key Vault and `az` paths are asserted to refuse before anything runs.

## Adding a guard rule

Add the pattern to `config/guard-policy.json` (or `patterns.py` for a value shape), add one blocked case and one
allowed case to the matching test module, and note the trade-off in the file's header comment if the rule can
produce false positives.

## Reporting a security issue

See `SECURITY.md`. Never include a real value in a report.

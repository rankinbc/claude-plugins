# Contributing

Thanks for your interest. Each plugin under `plugins/` is self-contained: its own
manifest, docs, tests and CI workflow. Most changes touch one plugin only.

## Try a plugin from a checkout

    git clone https://github.com/rankinbc/claude-plugins
    claude --plugin-dir claude-plugins/plugins/<name>

Or add your checkout as a local marketplace: `/plugin marketplace add ./claude-plugins`.

## Run the tests

| Plugin | Commands (from the plugin folder) |
|---|---|
| recursive-research | `python -m unittest discover -s tests` |
| secret-courier | `python -m pip install -e ".[dev]"`, then `python -m ruff check src tests scripts`, `python -m pytest -q`, and `Invoke-Pester -Path powershell/tests` (Pester 5+) |
| project-scaffolder | `python -m unittest discover -s tests` (needs `sh`; Git Bash on Windows) |

From the repository root, `python scripts/check_marketplace.py` checks that the
marketplace, the plugin manifests and the changelogs agree, and
`claude plugin validate plugins/<name>` checks a plugin the way Claude Code loads it.

Each plugin folder may have its own `CONTRIBUTING.md` or `CLAUDE.md` with rules
specific to it; secret-courier's are strict and enforced by its tests.

## Making a change

1. Keep the change inside one plugin folder where you can.
2. Add or update tests for behaviour you change.
3. Add a line to the plugin's `CHANGELOG.md` under its unreleased version.
4. Never commit a real secret, token or key, not even an expired one. Build test
   values at runtime.

## Releasing (maintainers)

1. Set the new version in `plugins/<name>/.claude-plugin/plugin.json` (and
   `pyproject.toml` for secret-courier) and date its `CHANGELOG.md` section.
2. Run `python scripts/check_marketplace.py --tag <name>--vX.Y.Z`.
3. Tag `<name>--vX.Y.Z` on `main` and push the tag. CI checks it again, then
   create the GitHub release from the tag with the changelog section as notes.

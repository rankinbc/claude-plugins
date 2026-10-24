# Changelog

All notable changes to project-scaffolder are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow semantic
versioning. Releases are tagged `project-scaffolder--vX.Y.Z`.

## 2.1.0 - Unreleased

### Changed

- Packaged as a Claude Code plugin in the [rankinbc/claude-plugins](https://github.com/rankinbc/claude-plugins)
  marketplace. Install with `/plugin install project-scaffolder@rankinbc` and run
  `/project-scaffolder:new-project` from any folder; no more cloning the kit.
- The new project lands in the current folder, or in `<slug>/` when the folder is
  not empty. An existing non-empty target is never overwritten.
- Generated projects commit `.claude/settings.json` (deny rules and the secret
  guard hook) and keep the allow list of common commands in a git-ignored
  `.claude/settings.local.json`, so cloning a project never pre-approves
  commands for someone else.

### Fixed

- Generated projects install: the root `pyproject.toml` declares a name, a
  version, explicit packages and a `dev` extra (pytest, ruff, mypy), so
  `pip install -e ".[dev]"` works with several components.
- Tests in several components run together (`--import-mode=importlib`), and
  mypy accepts them (`explicit_package_bases`).
- The `.env` guard hook fails closed: it finds a working Python (`python3`,
  `python`, `py -3`, skipping the Windows Store stub) and blocks the call when
  none works or the hook crashes. It catches case changes, wildcards, quote
  splitting and whole-project recursive searches, and covers the file and
  search tools as well as shell commands. Docs describe it as a guardrail, not
  a sandbox.
- `.env.example`, `.env.sample` and `.env.template` stay readable.
- Secret key names from the interview reach the scaffolding and validation
  agents, so `.env.example` lists the right keys.
- Launching the build from Git Bash on Windows works.
- Generated instructions name `python3` on macOS and Linux and run PowerShell
  scripts with `-ExecutionPolicy Bypass`; scripts parse under Windows
  PowerShell 5.1.
- One consistent list of the five slash commands everywhere; renumbered steps;
  the repo hygiene test no longer skips component folders named `build` or
  `data`.

### Added

- `tests/` for the plugin itself: the secret guard's verdicts on 150+ commands
  and payloads, the settings split, and every `${CLAUDE_PLUGIN_ROOT}` path the
  command and agents reference.

## 2.0.0

Scaffolded projects are recorded as `scaffold_version: 2`.

- Per-component `CLAUDE.md` files, loaded only when Claude works in that
  component.
- One `.env` at the project root, kept from Claude by `permissions.deny`, and a
  PowerShell script that fills it without a value entering the conversation.
- One root `pyproject.toml` and one install command.
- pytest and ruff configured for compact output.
- A hygiene test enforcing the file-size and artifact-placement rules.

## 1.0.0

First version: the `/new-project` interview, component patterns, parallel
research and planning agents, and a PRP-driven v1 build plan.

# CLAUDE.md — project-scaffolder plugin

This folder is the source of the **project-scaffolder** Claude Code plugin, inside the `rankinbc/claude-plugins` marketplace monorepo. Users never open Claude Code here: they install the plugin (`/plugin install project-scaffolder@rankinbc`) and run `/project-scaffolder:new-project` from an empty folder, which becomes their new project. This file is loaded only when someone works on the plugin itself.

When the plugin is installed, the command and agents read the plugin's own files through `${CLAUDE_PLUGIN_ROOT}` (the install folder). Every file they write goes into the target project, which defaults to the user's current working directory. Keep that split when you edit `commands/` or `agents/`: plugin files are referenced as `${CLAUDE_PLUGIN_ROOT}/...`, project files as plain relative paths.

If `HANDOFF.md` exists in this folder, a previous session paused mid-work — read it first.

---

## The 3-step flow (what `/new-project` produces and what comes after)

### Step 1 — Scaffold (in the user's empty folder)

User runs `/project-scaffolder:new-project`. The command (defined in `commands/new-project.md`):

- Interviews the user adaptively (~4-7 minutes)
- Decomposes their intent into named **components**, each matched to a pattern in `patterns/`
- Dispatches parallel `ce-researcher` sub-agents for per-component research
- Proposes a project structure for the user to approve
- Dispatches parallel `ce-scaffold` sub-agents to write each component's folder
- Synthesizes `PRPs/v1_<slug>.md` directly (no intermediate `/generate-prp` step for the v1 build)
- Writes `.scaffolding/manifest.json` + `.scaffolding/README.md` (transient state, auto-deleted on first successful build)
- Prints the exact `cd <path> && claude` command for the user to switch into their new project

### Step 2 — Open the new project

The user runs `cd <new-project-path> && claude` in a fresh terminal. They're now inside their scaffolded project, which has its own `CLAUDE.md` (from `deploy/CLAUDE.md`) governing behavior there.

### Step 3 — Build (`/execute-prp PRPs/v1_<slug>.md`)

Inside the new project, the user runs `/execute-prp PRPs/v1_<slug>.md`. Claude works through the plan, fills the stubs with real code, runs validation gates, and on success deletes `.scaffolding/` — leaving the project clean.

`/generate-prp` is **not** part of the initial v1 build. It's only used post-build for *new* features (typically via `/new-feature`'s guided flow, which interviews the user, fills `PRPs/source/INITIAL.md`, then chains into `/generate-prp` → `/execute-prp`).

---

## Repo layout (for when you need to find something)

```
plugins/project-scaffolder/
├── .claude-plugin/plugin.json  # Plugin manifest (name, version)
├── README.md                 # User-facing pitch + install
├── QUICK-START.md            # Install + the 3 steps
├── CLAUDE.md                 # This file
├── docs/GUIDE.md             # Longer end-user walkthrough
├── agents/                   # Sub-agents used by /new-project (namespaced project-scaffolder:ce-*)
│   ├── ce-researcher.md      # Per-component research (parallel)
│   ├── ce-planner.md         # Multi-component design proposal
│   ├── ce-scaffold.md        # Per-component folder writer (parallel)
│   └── ce-validator.md       # Post-scaffold structural checks
├── commands/
│   ├── new-project.md        # THE entry point (/project-scaffolder:new-project)
│   └── handoff.md            # Pause + resume (/project-scaffolder:handoff)
├── deploy/                   # Everything /new-project copies into scaffolded projects
│   ├── CLAUDE.md             # Project-level rules (ships into every new project)
│   ├── INITIAL.md            # Per-feature intake template
│   ├── .gitignore            # Multi-language defaults
│   ├── .claude/
│   │   ├── settings.local.json   # Permissions — allow list + deny rules blocking .env reads
│   │   ├── commands/         # /new-feature, /generate-prp, /execute-prp, /handoff, /deploy-status
│   │   └── hooks/            # block_secret_access.py — PreToolUse guard on .env
│   ├── scripts/secure/       # Set-ProjectSecrets.ps1, Test-Readiness.ps1 (copied only when a project declares secrets)
│   ├── tests/                # test_repo_hygiene.py — enforces the 500-line rule in scaffolded projects
│   └── PRPs/                 # Base PRP template + canonical guide
└── patterns/                 # Pattern shapes (dashboard, tracker, api, analysis, etc.)
```

Two distinct buckets: files **under `deploy/`** ship into every scaffolded project; files **outside `deploy/`** stay in the plugin and run during scaffolding.

---

## Kit development

Only relevant when the user is editing the scaffolder itself, not creating a new project.

- **Anything under `deploy/` ships to every scaffolded project forever.** Be careful — bloat hurts every user.
- **Keep `deploy/CLAUDE.md` lean.** Scaffolded projects inherit it.
- **Patterns evolve.** If you find yourself adjusting a scaffolded project post-hoc in ways `/new-project` should've gotten right, update `patterns/<shape>.md`.
- **Test new `deploy/.claude/commands/` slash commands inside a scaffolded project**, not here.
- **Test `commands/` and `agents/` changes as an installed plugin** (`claude --plugin-dir plugins/project-scaffolder` from an empty folder), so `${CLAUDE_PLUGIN_ROOT}` and the agent namespace behave as they do for users.
- **Don't put kit-dev plans under `deploy/PRPs/`** — those ship to users. Keep plugin-dev planning docs out of `deploy/`.

### Context discipline (kit work)

- `new-project.md` is ~850 lines — scout with grep before reading in full.
- For multi-file consistency checks across `patterns/` or `agents/`, dispatch `Explore` or `general-purpose` sub-agents instead of opening many files in the main session.
- Propose `/handoff` if a kit-dev session runs long.

### What NOT to do

- Don't put project-level rules (Python conventions, pytest patterns, etc.) here — that's `deploy/CLAUDE.md`'s job.
- Don't add interactive stdin prompts to `/new-project` — Claude Code doesn't support true mid-session stdin.
- Don't make `/new-project` silently pick stacks the user didn't approve — always show the proposal first.
- Don't add files at the kit root that should be in `deploy/`. If it gets injected into scaffolded projects, it lives in `deploy/`.

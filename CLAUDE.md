# CLAUDE.md — claude-prp-scaffold

This folder is a **scaffolder** for new Claude Code projects, not a project itself. When a user opens Claude Code here, they almost always want one of two things:

1. **Help creating a new Claude Code project** — the primary use case. Route them to `/new-project`.
2. **Editing the scaffolder itself** — they're maintaining patterns, sub-agents, or the deploy assets. See "Kit development" below.

Default to (1) unless the user makes (2) explicit.

---

## When a user opens Claude here

If their first message is anything like *"I want to build X"*, *"help me start a project"*, *"can you make me a dashboard / API / tool"*, or just a vague *"hi"* with no clear task — the right response is to point them at `/new-project`, briefly explain what it does, and let them run it.

Do **not** start writing code in this folder. This folder is the scaffolder; the user's project will be created in a different directory.

A good first response looks like:

> This folder is a scaffolder for new Claude Code projects. To get started, type `/new-project` — I'll run a short guided interview, research the components in parallel, and scaffold a full project (folder layout, conventions, slash commands, and a v1 build plan).
>
> The full flow is 3 steps:
> 1. `/new-project` here — scaffolds your new project
> 2. `cd` into the new project and open Claude Code there
> 3. `/execute-prp PRPs/v1_<slug>.md` — Claude builds the components from the plan

Then wait for them to run `/new-project`. Don't pre-emptively interview them — `/new-project` does that.

If `HANDOFF.md` exists at the kit root, a previous session paused mid-work — read it first.

---

## The 3-step flow (what `/new-project` produces and what comes after)

### Step 1 — Scaffold (in this folder)

User runs `/new-project`. The command (defined in `.claude/commands/new-project.md`):

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
<kit>/
├── README.md                 # User-facing pitch + 3 steps
├── CLAUDE.md                 # This file
├── docs/GUIDE.md             # Longer end-user walkthrough
├── .claude/
│   ├── agents/               # Sub-agents used by /new-project
│   │   ├── ce-researcher.md  # Per-component research (parallel)
│   │   ├── ce-planner.md     # Multi-component design proposal
│   │   ├── ce-scaffold.md    # Per-component folder writer (parallel)
│   │   └── ce-validator.md   # Post-scaffold structural checks
│   └── commands/
│       ├── new-project.md    # THE entry point
│       └── handoff.md        # Pause + resume
├── deploy/                   # Everything /new-project copies into scaffolded projects
│   ├── CLAUDE.md             # Project-level rules (ships into every new project)
│   ├── INITIAL.md            # Per-feature intake template
│   ├── .gitignore            # Multi-language defaults
│   ├── .claude/
│   │   ├── settings.local.json   # Permissions — allow list + deny rules blocking .env reads
│   │   └── commands/         # /new-feature, /generate-prp, /execute-prp, /handoff, /deploy-status
│   ├── scripts/secure/       # Set-ProjectSecrets.ps1, Test-Readiness.ps1 (copied only when a project declares secrets)
│   ├── tests/                # test_repo_hygiene.py — enforces the 500-line rule in scaffolded projects
│   └── PRPs/                 # Base PRP template + canonical guide
└── patterns/                 # Pattern shapes (dashboard, tracker, api, analysis, etc.)
```

Two distinct buckets: files **under `deploy/`** ship into every scaffolded project; files **outside `deploy/`** stay in the kit and run during scaffolding.

---

## Kit development

Only relevant when the user is editing the scaffolder itself, not creating a new project.

- **Anything under `deploy/` ships to every scaffolded project forever.** Be careful — bloat hurts every user.
- **Keep `deploy/CLAUDE.md` lean.** Scaffolded projects inherit it.
- **Patterns evolve.** If you find yourself adjusting a scaffolded project post-hoc in ways `/new-project` should've gotten right, update `patterns/<shape>.md`.
- **Test new `deploy/.claude/commands/` slash commands inside a scaffolded project**, not in the kit.
- **Don't put kit-dev plans under `deploy/PRPs/`** — those ship to users. Use the kit root for kit-dev planning docs.

### Context discipline (kit work)

- `new-project.md` is ~850 lines — scout with grep before reading in full.
- For multi-file consistency checks across `patterns/` or `agents/`, dispatch `Explore` or `general-purpose` sub-agents instead of opening many files in the main session.
- Propose `/handoff` if a kit-dev session runs long.

### What NOT to do

- Don't put project-level rules (Python conventions, pytest patterns, etc.) here — that's `deploy/CLAUDE.md`'s job.
- Don't add interactive stdin prompts to `/new-project` — Claude Code doesn't support true mid-session stdin.
- Don't make `/new-project` silently pick stacks the user didn't approve — always show the proposal first.
- Don't add files at the kit root that should be in `deploy/`. If it gets injected into scaffolded projects, it lives in `deploy/`.

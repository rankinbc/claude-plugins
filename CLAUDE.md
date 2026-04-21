# CLAUDE.md — Kit Development

You're in the **scaffolder** repo. This isn't a project; it's a scaffolder that creates projects. Two distinct activities happen here:

1. **End-user usage** — someone runs `/new-project` and Claude scaffolds a project folder for them. Most interactions are this.
2. **Kit development** — you're editing the scaffolder itself (improving `/new-project`, adding patterns, tuning sub-agents).

This file is for both. For **project-level** rules (the ones Claude follows *inside* a scaffolded project), see [`deploy/CLAUDE.md`](./deploy/CLAUDE.md) — that's what gets injected into every scaffolded project.

---

## Repo layout

```
<kit>/
├── README.md                 # Kit pitch + architecture
├── CLAUDE.md                 # This file — kit-dev orientation
├── .claude/
│   ├── settings.local.json   # Kit-session permissions
│   ├── agents/               # Sub-agents used by /new-project
│   │   ├── ce-researcher.md  # Per-component research (parallel)
│   │   ├── ce-planner.md     # Multi-component design proposal
│   │   ├── ce-scaffold.md    # Per-component folder writer (parallel)
│   │   └── ce-validator.md   # Post-scaffold structural checks
│   └── commands/
│       └── new-project.md    # THE entry point
├── deploy/                   # Everything /new-project injects into scaffolded projects
│   ├── CLAUDE.md             # Multi-language project rules
│   ├── INITIAL.md            # Base intake template
│   ├── .gitignore            # Multi-language defaults
│   ├── .claude/
│   │   ├── settings.local.json
│   │   └── commands/         # /generate-prp, /execute-prp, /handoff
│   └── PRPs/                 # Base PRP template + canonical guide
├── patterns/                 # Shape definitions (dashboard, tracker, api, etc.)
└── use-cases/                # Upstream's 7 use-cases preserved
```

**The split matters**:
- Files under `deploy/` get copied into every scaffolded project by `/new-project`. Edit them when you want to change what ships to users.
- Files NOT under `deploy/` (patterns, agents, new-project command) stay in the kit. They're used DURING scaffolding but aren't part of the scaffolded project.

---

## How `/new-project` works (for when you're debugging it)

A scaffolded project is a workspace with 1-N named **components**. Each component maps to one pattern from `patterns/`. The project is the container; components are what do the work.

```
User runs /new-project
  │
  ▼
Main session (this command) runs the conversation:
  ├─► Interviews user (adaptive Q&A)
  ├─► Decomposes intent into components (name + pattern each)
  ├─► Flow discussion — inputs/outputs per component
  ├─► Proposes project structure (tree + data flow)
  ├─► Dispatches Task tool: subagent_type="ce-researcher"  (parallel, one per component)
  ├─► Dispatches Task tool: subagent_type="ce-planner"     (after all research returns)
  ├─► Shows multi-component design proposal; iterates if needed
  ├─► Scaffolds project-root files + folder skeleton (components/, data/<source>/, output/<component>/)
  ├─► Dispatches Task tool: subagent_type="ce-scaffold"    (parallel, one per component — writes each components/<name>/)
  ├─► Builds project CLAUDE.md dynamically from ce-scaffold returns (enforcement rules + per-component gotchas + aggregated validation)
  ├─► Dispatches Task tool: subagent_type="ce-validator"   (post-scaffold)
  └─► Hands off to user with next-step instructions
```

Sub-agents are defined in `.claude/agents/`. `ce-scaffold` reads patterns from `patterns/<shape>.md` to write each component's internal structure. Project-level structure (`components/`, `data/`, `output/`) is enforced via the dynamically-generated CLAUDE.md in the scaffolded project.

---

## Context Discipline (for kit work)

These rules keep the kit maintainable:

- **Scout large files before reading fully.** `new-project.md` is ~300 lines; don't re-read in full unless necessary.
- **Use sub-agents for multi-file research.** When checking consistency across `patterns/`, dispatch Explore or general-purpose — don't open 10 files in the main session.
- **Externalize long-running plans.** If a change spans many files, write a plan doc at the kit root (e.g. `KIT_PLAN.md`, gitignored or committed — your call). Don't put kit-dev plans under `deploy/PRPs/` — those ship into every scaffolded project.
- **Propose `/handoff`** if the session runs long. (The `/handoff` command is defined at the kit level in `.claude/commands/handoff.md`; it writes `HANDOFF.md` at the kit root.)

---

## Editing discipline

When you edit something in `deploy/`, you're changing what ships to every scaffolded project forever. A few rules:

- **Deploy-side assets stay language-agnostic** (or make the language-specificity additive, not replacing).
- **Keep `deploy/CLAUDE.md` lean.** Scaffolded projects inherit it; bloat hurts every user.
- **If you add a slash command to `deploy/.claude/commands/`**, test it in a scaffolded project, not in the kit.
- **Patterns evolve** — if you find yourself adjusting a scaffolded project post-hoc in ways that `/new-project` should've gotten right, that's a signal to update `patterns/<shape>.md`.

---

## What NOT to do

- Don't put project-level rules (Python patterns, pytest conventions, etc.) in this CLAUDE.md — that's `deploy/CLAUDE.md`'s job
- Don't edit files in `use-cases/` — those are upstream, preserved as-is
- Don't add interactive prompts to `/new-project` that block on stdin — Claude Code doesn't support true stdin prompts mid-session
- Don't make `/new-project` silently pick stacks the user didn't want — always show the proposal before scaffolding
- Don't add files to the kit root that should really be in `deploy/`. If it gets injected into scaffolded projects, it lives in `deploy/`.

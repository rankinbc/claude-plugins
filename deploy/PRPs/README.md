# PRPs — Product Requirements Prompts

Canonical reference for the PRP system in this project. Read this if the `PRPs/` folder confuses you, or before diving into any other file in it.

---

## What is a PRP?

A **Product Requirements Prompt** is a detailed implementation blueprint written *for* an AI coding assistant (Claude). It contains everything needed to implement a deliverable end-to-end without further research:

- Full context (what's being built, why, key constraints)
- Documentation references (APIs, libraries, internal files to read)
- Implementation steps in order
- Validation gates (commands to run — tests, linters — that must pass)
- Error handling patterns
- Success criteria

A PRP is not a conversation; it's a file. Once generated, it can drive an implementation session without the planning context — which matters because clean, focused sessions produce better code.

---

## PRP vs PRD — what's the difference?

| | PRD (Product Requirements Document) | PRP (Product Requirements Prompt) |
|---|---|---|
| **Audience** | Humans — PMs, engineers, designers | AI coding assistants |
| **Purpose** | Align stakeholders on what to build | Give the AI enough context to implement it |
| **Content** | User stories, business goals, mockups, success metrics | Executable steps, code patterns to follow, validation commands, gotchas |
| **Typical length** | 5-50 pages, narrative | 100-800 lines, structured |
| **Lifecycle** | Created once, referenced during planning | Generated per deliverable, executed once, then the code is the artifact |

PRDs are still useful — they answer "why are we building this?" for the team. PRPs answer "exactly what and how does the AI build this?" Both can coexist.

---

## Two workflows — initial build vs. post-build features

This project has two PRP workflows. Knowing which you're in matters.

### 1. Initial v1 build (one command)

When `/new-project` scaffolded this project, it wrote your v1 implementation plan directly:

```
PRPs/v1_<slug>.md  →  /execute-prp PRPs/v1_<slug>.md
```

No `INITIAL.md` middleman, no `/generate-prp` step. The PRP is already here. Just run:

```
/execute-prp PRPs/v1_<slug>.md
```

Claude fills in the component stubs with real code, runs validation gates, archives the PRP on success, and cleans up scaffolder state (`.scaffolding/` folder + README status banner). You end up with a clean, working v1.

**Partial build:** if you only want to build one component now, pass `--component <name>`:

```
/execute-prp PRPs/v1_<slug>.md --component <name>
```

Other components stay as stubs; lifecycle stays at `"plan"` until all are built.

### 2. Post-build feature work

Once v1 is built, the easiest path is **`/new-feature`** — a guided interview that asks a few questions, fills `PRPs/source/INITIAL.md` for you, and chains into `/generate-prp` and `/execute-prp`:

```
/new-feature  →  PRPs/source/INITIAL.md  →  /generate-prp  →  PRPs/<slug>.md  →  /execute-prp PRPs/<slug>.md
```

Prefer to author the spec yourself? Edit `PRPs/source/INITIAL.md` directly, then:

- `/generate-prp` (no arg — reads `PRPs/source/INITIAL.md` by default) researches your codebase + external patterns and writes `PRPs/<slug>.md`
- `/execute-prp PRPs/<slug>.md` implements it, runs validation, archives on success

Trivial fixes (typos, one-line bug fixes) don't need a PRP or `/new-feature`. Just ask Claude directly.

---

## File organization

```
PRPs/
├── README.md                      # This file
├── v1_<slug>.md                   # Your v1 implementation plan (initial build only — archived after /execute-prp)
├── <feature>.md                   # Active post-build PRPs waiting to run
├── templates/
│   └── prp_base.md                # Structural template /generate-prp follows (don't edit)
├── archive/
│   └── <YYYY-MM-DD>_<slug>.md     # Completed PRPs. /execute-prp moves them here on success.
└── source/
    └── INITIAL.md                 # Blank per-feature intake template — edit for each new feature post-build
```

### Naming conventions

- **Initial v1 build**: `v1_<slug>.md` (written by `/new-project`)
- **Post-build features**: `<slug>.md` — slug derived from the INITIAL file's feature description (e.g., `user-auth.md`, `csv-importer.md`)

`templates/prp_base.md` is the blueprint the generator uses. **Don't edit it during feature work** — it's infrastructure, not content.

### Lifecycle — automatic cleanup

- From scaffold onward, `INITIAL.md` lives at `PRPs/source/INITIAL.md` as a blank per-feature template. No file moves under your feet.
- `/generate-prp` (no arg) reads `PRPs/source/INITIAL.md` and writes a new active PRP to `PRPs/<slug>.md`.
- `/execute-prp`, on success, moves the executed PRP to `PRPs/archive/<YYYY-MM-DD>_<slug>.md`. Failed or interrupted runs leave the PRP in place so the next session can pick it back up.
- `/execute-prp` on a **first successful v1 build** additionally deletes the `.scaffolding/` folder and strips the status banner from `README.md` — the scaffolder leaves no trace.
- Treat files under `archive/` as historical reference, not active work. They're still readable; grep them if you need context on a past plan.

---

## When to read which file

| Situation | Read |
|---|---|
| First time in this project (pre-build) | `../CLAUDE.md` → `../README.md` → `../.scaffolding/README.md` → `v1_<slug>.md` |
| First time in this project (post-build) | `../CLAUDE.md` → `../README.md` → this file |
| Starting a new feature (post-build, guided) | Run `/new-feature` — no reading needed |
| Writing a new feature spec by hand (post-build) | `./source/INITIAL.md` |
| Curious how PRPs are structured internally | `./templates/prp_base.md` |
| Resuming tomorrow | `../HANDOFF.md` (if it exists) |

---

## Glossary

- **PRP** — Product Requirements Prompt. A generated implementation blueprint for Claude.
- **PRD** — Product Requirements Document. The traditional human-audience spec.
- **INITIAL.md** — Blank per-feature intake template (at `PRPs/source/INITIAL.md`). Edit to describe a post-build feature, then run `/generate-prp`. NOT used for the initial v1 build.
- **v1 mega-PRP** — The multi-component implementation plan at `PRPs/v1_<slug>.md`, written by `/new-project` at scaffold time for the initial build.
- **Validation gate** — An executable check (tests, linter, type-checker) included in a PRP that must pass before the implementation is considered done.
- **`/new-feature`** — Slash command: guided interview that fills `PRPs/source/INITIAL.md` for a new feature, then chains to `/generate-prp` and `/execute-prp`. Post-build only. The friendly entry point for new work.
- **`/generate-prp`** — Slash command that reads `PRPs/source/INITIAL.md` (or a path you pass), does research, writes a complete PRP. Used for **post-build feature work** — NOT for initial v1 build. Called automatically by `/new-feature`, or run directly if you hand-authored INITIAL.md.
- **`/execute-prp`** — Slash command that reads a PRP and implements the feature. Used for both initial build (`PRPs/v1_<slug>.md`) and post-build features.
- **`--component <name>`** — Optional flag on `/execute-prp` to build only one section of a multi-component PRP. Useful for partial rebuilds.
- **`.scaffolding/`** — Hidden folder holding transient scaffolder state (manifest, first-run notes). Auto-deleted by `/execute-prp` on successful v1 build.
- **`/handoff`** — Slash command that saves session state to `HANDOFF.md` for resume-tomorrow continuity.

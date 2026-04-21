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
| **Typical length** | 5-50 pages, narrative | 100-500 lines, structured |
| **Lifecycle** | Created once, referenced during planning | Generated per deliverable, executed once, then the code is the artifact |

PRDs are still useful — they answer "why are we building this?" for the team. PRPs answer "exactly what and how does the AI build this?" Both can coexist.

---

## The workflow

```
INITIAL.md  →  /generate-prp INITIAL.md  →  PRPs/<project-or-feature>.md  →  /execute-prp PRPs/<...>.md
```

Two commands. Claude does the research, writing, and implementation:

- You describe what you want in `INITIAL.md` (may already be filled in from when the project was created)
- `/generate-prp INITIAL.md` — Claude researches your codebase + external patterns, writes a full PRP to `PRPs/<slug>.md`
- `/execute-prp PRPs/<slug>.md` — Claude reads the PRP and implements it, running validation at each step

Works for features, tools, data analyses, integrations, CLI utilities — anything where the output is code or artifacts that run in this project.

### Multi-component projects

If `INITIAL.md` has one or more `### COMPONENT: <name>` blocks (the shape produced by `/new-project`), `/generate-prp` produces **one PRP that covers all components** — a mega-PRP with per-component sections, inter-component ordering based on the data flow, and aggregated validation gates. `/execute-prp` then builds the components in the right order in a single plan.

---

## File organization

```
PRPs/
├── README.md                      # This file
├── templates/
│   └── prp_base.md                # Structural template /generate-prp follows (don't edit)
├── <feature>.md                   # Active PRPs — waiting to run, or currently executing
├── archive/
│   └── <YYYY-MM-DD>_<slug>.md     # Completed PRPs. /execute-prp moves them here on success.
└── source/
    └── INITIAL.md                 # Project intake, relocated here after first /generate-prp
```

### Naming conventions

Generated PRPs are named by slug from `INITIAL.md`'s feature description. Examples:
- `PRPs/user-auth.md`
- `PRPs/csv-importer.md`
- `PRPs/sales-analysis.md`

`templates/prp_base.md` is the blueprint the generator uses. **Don't edit it during feature work** — it's infrastructure, not content.

### Lifecycle — the PRPs folder stays clean automatically

- `/generate-prp` writes a new active PRP to `PRPs/<slug>.md`.
- On the first successful run, `/generate-prp` also relocates root `INITIAL.md` to `PRPs/source/INITIAL.md`. Subsequent runs read from there. This keeps the project root minimal.
- `/execute-prp`, when it completes successfully (all validation gates pass), moves the executed PRP to `PRPs/archive/<YYYY-MM-DD>_<slug>.md`. Failed or interrupted runs leave the PRP in place so the next session can pick it back up.
- Treat files under `archive/` as historical reference, not active work. They're still readable; grep them if you need context on a past plan.

---

## Building a second feature

Once your first feature is done, add another:

1. Edit `INITIAL.md` with the new feature (or write a new file like `INITIAL_auth.md`)
2. Run `/generate-prp INITIAL.md` (or `/generate-prp INITIAL_auth.md`)
3. Run `/execute-prp PRPs/<new-slug>.md`

The `INITIAL.md` form is reusable — overwrite it or keep copies per feature, whatever feels better.

---

## When to read which file

| Situation | Read |
|---|---|
| First time in this project | `../CLAUDE.md` → `../README.md` → this file |
| Writing a new feature spec | `../INITIAL.md` |
| Curious how PRPs are structured internally | `./templates/prp_base.md` |
| Resuming tomorrow | `../HANDOFF.md` (if it exists) |

---

## Glossary

- **PRP** — Product Requirements Prompt. A generated implementation blueprint for Claude.
- **PRD** — Product Requirements Document. The traditional human-audience spec.
- **INITIAL.md** — The intake form describing what you want built.
- **Validation gate** — An executable check (tests, linter, type-checker) included in a PRP that must pass before the implementation is considered done.
- **`/generate-prp`** — Slash command that reads `INITIAL.md`, does research, writes a complete PRP.
- **`/execute-prp`** — Slash command that reads a PRP and implements the feature.
- **`/handoff`** — Slash command that saves session state to `HANDOFF.md` for resume-tomorrow continuity.

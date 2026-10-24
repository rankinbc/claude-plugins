# Component-Shape Patterns

Internal reference for `/new-project`. Each file describes a **shape** — a family of project *components* with similar structure, stack, and conventions.

A scaffolded project consists of 1-N components. Each component maps to exactly one pattern. The same project can mix patterns — e.g., a `cli.md` component that pulls data, an `analysis.md` component that processes it, and a `report.md` component that summarizes it.

When `/new-project` classifies each component's purpose, it picks a matching pattern file and reads it for:

- **Default stack** — what technology makes sense for this shape
- **Folder structure** — what goes inside `components/<name>/`
- **Starter code** — **reference idiom** for `/execute-prp` to follow during the build stage. The scaffolder ships only minimum-viable stubs; the real implementation, guided by this reference code plus the pattern's gotchas, gets written by `/execute-prp`.
- **Gotchas** — shape-specific things to bake into the project CLAUDE.md
- **Validation approach** — what counts as "working" for this shape

These files are **not** deployed to scaffolded projects. They're internal to the kit. Users never see them.

## Available shapes

| File | When to use |
|---|---|
| `dashboard.md` | Interactive view of existing data |
| `tracker.md` | Simple list/status of items |
| `research.md` | Knowledge work — gather, synthesize, deliver a report |
| `analysis.md` | Examine a dataset, produce findings |
| `report.md` | Recurring report (weekly/monthly/quarterly) combining data + narrative |
| `product_doc.md` | PRD, one-pager, launch brief, or other product document |
| `form_view.md` | Form input → stored → summary view |
| `automation.md` | Runs on a schedule, processes things, notifies |
| `api.md` | CRUD API with auth |
| `cli.md` | Command-line tool |
| `integration.md` | System-to-system sync |

## Adding new shapes

If `/new-project` classifies a component and nothing fits cleanly:

1. Propose a design anyway (scaffold based on the closest existing shape + customization)
2. After scaffolding, ask yourself: is this a new recurring shape?
3. If yes, consider adding a new `patterns/<name>.md` file for future use (via a PR)

## Writing a new pattern — conventions

Patterns are consumed by `ce-scaffold` (per-component scaffolding) and read by `/new-project` (for project `CLAUDE.md` gotchas + validation aggregation). Each pattern section has a defined **consumer** — where the content ends up or who reads it. Keep these section headers so parsing works.

### Sections that feed a `CLAUDE.md` (Claude-facing rules)

- `## Gotchas for CLAUDE.md` — ce-scaffold writes these bullets directly into `components/<name>/CLAUDE.md`. They are **not** returned to the main session and never appear in the project root `CLAUDE.md`. Claude Code loads subdirectory `CLAUDE.md` files on demand, so a five-component project pays for one component's gotchas only when it works on that component.
- `## Validation` — commands ce-scaffold returns in its report; the main session aggregates them into the project root `CLAUDE.md` validation gates block. These stay at the root because `/execute-prp` needs the full list in one place, and keeping a single copy stops root and component drifting apart.

Anything Claude should *follow* when editing the component lives in these two sections only.

### Sections that feed the component `README.md` (human-facing overview)

- `## Default stack` — surfaced in the "Stack" line of the component README
- `## Folder structure (component-internal)` — summarized in the "Structure" section of the README (component-internal only — don't include project-level folders like `data/` or `output/`)

### Sections that drive scaffolding but don't land in any doc

- `## Starter files` or `## Starter code` — **reference idiom** for `/execute-prp`, not code the scaffolder ships. `ce-scaffold` reads this section only to identify *which files* the pattern expects (by filename) and their stack. It then writes minimum-viable stubs (imports + trivial demo + TODO) — never the pattern's real code. Reference inputs/outputs in stubs using relative paths (`../../data/<source>/`, `../../output/<component>/<date>_<run>/`). The code blocks below are what `/execute-prp` uses as the build target, not what ships at scaffold time.

### Sections that surface via `ce-researcher` and propose project-level structure

- `## Project-level footprint` — optional. Folders components of this shape often benefit from at the **project root** (not inside the component). `ce-researcher` forwards these verbatim in its return; `ce-planner` aggregates + dedupes across all components in the project, then the main session proposes the set to the user during design iteration. Approved folders get scaffolded with one-line README stubs and documented in the project's `CLAUDE.md` structure block. Format: bulleted list, each bullet `` `folder_name/` — one-line purpose. ``. Most patterns don't need this; omit the section entirely when there's no cross-component shared-structure need.

### Kit-internal sections (never emitted to scaffolded projects)

- `## INITIAL.md pre-fill hints` — read by `/new-project` to populate the project root `INITIAL.md`
- `## Interview follow-ups` — shape-specific questions for `/new-project`'s scoping conversation

### Project-root concerns a pattern must NOT scaffold into the component

Three things consolidated to the project root. A pattern's `## Folder structure (component-internal)` must not list any of them inside the component:

- **Dependencies** — no component-local `requirements.txt` / `pyproject.toml` / `package.json`. List the libs in `## Default stack`; ce-scaffold reports them and the main session writes one root manifest. One project, one environment, one install.
- **Secrets** — no component-local `.env.example`. Name the keys in `## Gotchas for CLAUDE.md`; ce-scaffold reports the names and the main session writes one root `.env.example`. Starter code loads `PROJECT_ROOT / ".env"`, never `COMPONENT_DIR / ".env"`.
- **Logs** — a component that logs writes to `../../output/<component>/<date>_<run>/run.log`, alongside that run's other artifacts.

**The rule**: README is for orientation (what this is, how to run it, how it's organized — human-facing). Gotchas live in `components/<name>/CLAUDE.md`; validation commands live in the project root `CLAUDE.md`'s gates block. A pattern section contributes to exactly one consumer.

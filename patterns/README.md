# Component-Shape Patterns

Internal reference for `/new-project`. Each file describes a **shape** — a family of project *components* with similar structure, stack, and conventions.

A scaffolded project consists of 1-N components. Each component maps to exactly one pattern. The same project can mix patterns — e.g., a `cli.md` component that pulls data, an `analysis.md` component that processes it, and a `report.md` component that summarizes it.

When `/new-project` classifies each component's purpose, it picks a matching pattern file and reads it for:

- **Default stack** — what technology makes sense for this shape
- **Folder structure** — what goes inside `components/<name>/`
- **Starter code** — minimal runnable skeleton (I/O paths rewritten to the project's shared `data/` and `output/` folders)
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

### Sections that feed the project `CLAUDE.md` (Claude-facing rules, aggregated)

- `## Gotchas for CLAUDE.md` — bullets ce-scaffold returns in its report; the main session writes them into the project root `CLAUDE.md` under that component's section
- `## Validation` — commands ce-scaffold returns; the main session aggregates them into the project root `CLAUDE.md` validation gates block

Anything Claude should *follow* when editing the component lives in these two sections only.

### Sections that feed the component `README.md` (human-facing overview)

- `## Default stack` — surfaced in the "Stack" line of the component README
- `## Folder structure to scaffold` — summarized in the "Structure" section of the README (component-internal only — don't include project-level folders like `data/` or `output/`)

### Sections that drive scaffolding but don't land in any doc

- `## Starter files` or `## Starter code` — the files `ce-scaffold` writes. Reference inputs/outputs using relative paths (`../../data/<source>/`, `../../output/<component>/<date>_<run>/`). The files themselves are the output; no prose goes into README or CLAUDE.md from here.

### Kit-internal sections (never emitted to scaffolded projects)

- `## INITIAL.md pre-fill hints` — read by `/new-project` to populate the project root `INITIAL.md`
- `## Interview follow-ups` — shape-specific questions for `/new-project`'s scoping conversation

**The rule**: README is for orientation (what this is, how to run it, how it's organized — human-facing). Gotchas and validation commands live in the project root `CLAUDE.md`'s per-component section — not the component README. A pattern section contributes to exactly one consumer.

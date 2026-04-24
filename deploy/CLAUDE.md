# CLAUDE.md — Project Rules

Language-agnostic defaults. Append your stack-specific section at the end.

---

### Session Start

- **Read `.scaffolding/manifest.json` first if it exists.** Check `lifecycle.stage`:
  - `"plan"` — the v1 implementation plan is written at `PRPs/v1_<slug>.md` but hasn't been executed. Components are stubs. On a fresh session, tell the user "**This project is at stage 1 of 2 (planned). Components are stubs — not yet runnable.** Next step: `/execute-prp PRPs/v1_<slug>.md`." Never suggest running component entry commands; they won't work yet.
  - `"built"` (rare — `/execute-prp` normally deletes `.scaffolding/` on first full build, so this state is only seen mid-partial-build) — some components built, others still stubs. Check individual `scaffold_state` values before claiming the project is ready.
  - `.scaffolding/` missing entirely — the common built-project case. `/execute-prp` cleaned up scaffolder state on first successful build. Treat the project as fully built; entry commands in CLAUDE.md's "How to run" are runnable. Adding new features uses `/generate-prp` (reads `PRPs/source/INITIAL.md`) → `/execute-prp PRPs/<new-slug>.md`.
- If `HANDOFF.md` exists, read it first — a previous session paused mid-work.
- Otherwise, if `PRPs/source/INITIAL.md` is filled in and no PRP exists in `PRPs/` yet, that's the project intent — suggest `/generate-prp` (no arg) as the next step.
- Consult `PRPs/README.md` if the PRP workflow comes up.
- Check `PLANNING.md` / `TASK.md` if they exist.

### Context Discipline

Keep long sessions coherent — follow these automatically.

- **Scout files >400 lines before full-reading.** Grep for the target section first; Read only the slice you need.
- **Dispatch sub-agents for multi-file research and web lookups** (Task tool: Explore, general-purpose, Plan). Don't pollute the main session.
- **Externalize multi-step plans to files.** Write PRPs under `PRPs/`. Plans in files survive context resets; plans in conversation don't.
- **Propose `/handoff` proactively** when context is heavy or the user's about to pause. Don't let long sessions silently degrade.

### Code

- **No file over ~500 lines.** Split when approaching the limit.
- **Organize by feature**, following the language's conventions.
- **Externalize config and secrets** via env vars. Never hardcode credentials.

### Testing

- **Unit tests for new features.** At minimum: one expected-use, one edge case, one failure case.
- **When you change logic**, update affected tests.

### Docs

- **Update `README.md`** when features change or setup changes.
- **Comment the non-obvious why**, not what the code does.

### AI Behavior

- **Ask if uncertain** — don't assume missing context.
- **No hallucinated libraries or APIs** — verify packages exist before using them.
- **Confirm file paths and symbols** before referencing them.
- **Don't delete or overwrite existing code** without explicit instruction.

### Workflow

- **Default to the PRP workflow for new work.** New features, components, or multi-step changes go through `/new-feature` → `/generate-prp` → `/execute-prp`. `/new-feature` is the guided entry point — it interviews the user and fills `PRPs/source/INITIAL.md`; `/generate-prp` researches and writes the PRP; `/execute-prp` builds it. If the user asks for non-trivial new work and no active (non-archived) PRP in `PRPs/` covers it, propose `/new-feature` first and briefly explain why — the validation gates and checkpoints are what keep long sessions coherent across resets. Trivial fixes (typos, one-line bug fixes, doc tweaks, minor refactors) don't need a PRP — just do them.

### Project Cleanliness

- **Respect the project structure** declared at the top of this file. Never create new top-level folders without updating the structure block first. Components live in `components/<name>/`, inputs in `data/<source>/`, outputs in `output/<component>/<date>_<description>/`.
- **Tool caches outside the project.** Configure your language's tools to cache under `~/.cache/<tool>/` (or equivalent). For Python: set cache dirs in `pyproject.toml` and `PYTHONDONTWRITEBYTECODE=1` in `.env`.
- **Descriptive file and folder names.** It should be obvious what's what from the name alone. Avoid `utils.py`, `data.csv`, `temp.txt` — prefer `csv_loader.py`, `sales_2024_q4.csv`, etc.
- **Generated artifacts** always land under `output/<component>/<date>_<description>/` — never at the project root. Other gitignored dirs (`dist/`, `build/`, `htmlcov/`) are fine where a toolchain expects them.
- **Output rotation.** Keep the latest ~5 runs directly under `output/<component>/`. Move older runs to `output/<component>/_archive/` so routine globs and exploration skip historical artifacts. The `_archive/` prefix is intentionally glob-unfriendly for that reason. No script enforces this — apply the convention when you notice a component's output folder growing past ~5 dated subdirectories.
- **PRP lifecycle.** Active plans live in `PRPs/`. On successful `/execute-prp`, the command moves the PRP to `PRPs/archive/<date>_<slug>.md` — don't treat files in `archive/` as current work. Your spec lives at `PRPs/source/INITIAL.md` from scaffold onward; edit it in place for the next feature.
- **Throwaway / single-use files** → prefix with `temp_` so they're easy to find and delete later.
- **Don't create files the user didn't ask for** — no `PLANNING.md`, `NOTES.md`, `TODO.md`, etc. unless requested.

### Task Completion

- **PRP workflow**: validation gates passing = work is done.
- **TASK.md projects**: mark complete immediately; add new sub-tasks under "Discovered During Work".

---

## Stack-specific rules

<!-- Describe your stack here. Example:
     Python 3.11 + FastAPI + SQLAlchemy 2.0. Test with pytest. Format
     with ruff. Pydantic v2 only. Avoid sync DB calls in async routes. -->

<!-- YOUR PROJECT-SPECIFIC RULES GO HERE -->

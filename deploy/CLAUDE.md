# CLAUDE.md — Project Rules

Language-agnostic defaults. Append your stack-specific section at the end.

---

### Session Start

- If `HANDOFF.md` exists, read it first — a previous session paused mid-work.
- Otherwise, if `INITIAL.md` is filled in and no PRP exists in `PRPs/` yet, that's the project intent — suggest `/generate-prp INITIAL.md` as the next step.
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

### Project Cleanliness

- **Respect the project structure** declared at the top of this file. Never create new top-level folders without updating the structure block first. Components live in `components/<name>/`, inputs in `data/<source>/`, outputs in `output/<component>/<date>_<description>/`.
- **Tool caches outside the project.** Configure your language's tools to cache under `~/.cache/<tool>/` (or equivalent). For Python: set cache dirs in `pyproject.toml` and `PYTHONDONTWRITEBYTECODE=1` in `.env`.
- **Descriptive file and folder names.** It should be obvious what's what from the name alone. Avoid `utils.py`, `data.csv`, `temp.txt` — prefer `csv_loader.py`, `sales_2024_q4.csv`, etc.
- **Generated artifacts** always land under `output/<component>/<date>_<description>/` — never at the project root. Other gitignored dirs (`dist/`, `build/`, `htmlcov/`) are fine where a toolchain expects them.
- **Output rotation.** Keep the latest ~5 runs directly under `output/<component>/`. Move older runs to `output/<component>/_archive/` so routine globs and exploration skip historical artifacts. The `_archive/` prefix is intentionally glob-unfriendly for that reason. No script enforces this — apply the convention when you notice a component's output folder growing past ~5 dated subdirectories.
- **PRP lifecycle.** Active plans live in `PRPs/`. On successful `/execute-prp`, the command moves the PRP to `PRPs/archive/<date>_<slug>.md` — don't treat files in `archive/` as current work. `INITIAL.md` relocates to `PRPs/source/` after the first `/generate-prp`.
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

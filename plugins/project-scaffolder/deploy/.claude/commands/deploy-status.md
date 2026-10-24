# Deploy Status

Read the project's state and print a report on deploy/build progress. No writes, no side effects — purely informational.

---

## Execution

### 1. Determine overall build state

Check for `.scaffolding/manifest.json` at the project root:

- **Present** — the project is pre-built or in partial-build state. Read the manifest. Extract `lifecycle.stage`, `components[]`, `project_name`, `project_slug`, `scaffolded_at`.
- **Absent** — the project is built. `/execute-prp` already cleaned up scaffolder state on first successful build. All components are done; there's nothing more to do for the v1 milestone. Rendering skips per-component inspection and goes straight to the post-build report (see §4b).

### 2. For each component, classify into done / in progress / incomplete

Only runs when the manifest is present.

- **Done** — `scaffold_state == "built"` in the manifest.
- **Incomplete** — `scaffold_state == "stub"` AND the component's primary source file still looks like a pristine scaffold stub (contains a `# TODO: /execute-prp fills this in` marker and is under ~30 lines, no real implementation).
- **In progress** — `scaffold_state == "stub"` but the primary source file has been modified beyond the pristine scaffold (TODO marker removed, or file has significant content). This happens if someone hand-edited a component without running `/execute-prp`, or if `/execute-prp` failed partway through filling in that component.

Identifying the "primary source file" per component: use the pattern-specific entry point — e.g., for `cli.md` components it's typically `components/<name>/src/<name>/cli.py` or `.../commands/<primary>.py`; for `analysis.md` components it's `components/<name>/scripts/run.py` or `analysis.py`. If unsure, look at the `entry_command` in the manifest for the component — it usually points at the primary file. Check existence and peek at the contents (first 30 lines); don't read the full file.

### 3. Check for active post-build feature PRPs

Look in `PRPs/` (not `PRPs/archive/`, not `PRPs/templates/`, not `PRPs/source/`, not `PRPs/README.md`) for any `*.md` files OTHER than `PRPs/v1_<slug>.md`. These are **active post-build feature PRPs** — either awaiting `/execute-prp` or interrupted mid-execution. List them as "pending / in-progress features."

### 3.5 Check configuration state

Only when `.env.example` exists at the project root. If it doesn't, this project declares no secrets — skip this step and omit the Configuration section from the report entirely.

Run the readiness script and use its output verbatim:

```bash
pwsh -File scripts/secure/Test-Readiness.ps1
```

It prints one line per declared key — `set`, `empty`, or `missing` — and **never prints a value**. Exit code 0 means everything is configured; 1 means something is unset.

- If the script can't run (no `pwsh` on PATH, script missing), report configuration state as **unknown** and tell the user to run it themselves. Do not fall back to reading `.env` — it's deny-listed, and that's deliberate.
- Never read `.env`, and never quote a value out of `.env.example`. Key names only.

### 4a. Render the pre-built / partial-build report

If the manifest is present. Use exactly this shape and ordering:

```markdown
## **PROJECT READY TO USE: NO**

{project_name} (scaffolded {scaffolded_at}). {one-sentence summary — e.g., "Lifecycle stage: plan. 0 of 3 components built."}

### Progress

| Component | Pattern | State | Entry command |
|---|---|---|---|
| {name} | {pattern} | {✅ DONE \| 🟡 IN PROGRESS \| ⬜ INCOMPLETE} | `{entry_command}` |
| ... | ... | ... | ... |

{If `.env.example` exists, add:}

### Configuration

{n}/{total} secrets set. {If any are unset, list the missing key NAMES and add: "Run `.\scripts\secure\Set-ProjectSecrets.ps1` in your own terminal — not through Claude — to fill them in."}

{If active post-build PRPs exist, add an "Active feature PRPs" section with a bulleted list of file paths.}

### Next step

{Explicit, copy-pasteable instruction. Branches:}

- **If all components are INCOMPLETE**: "Run `/execute-prp PRPs/v1_{slug}.md` to build all components. This is the full v1 build."
- **If some INCOMPLETE + some DONE**: "Resume the v1 build. Run `/execute-prp PRPs/v1_{slug}.md --component {first_incomplete_name}` to build the next component, or `/execute-prp PRPs/v1_{slug}.md` to build everything remaining."
- **If some IN PROGRESS**: "The component `{name}` has been modified beyond its stub. Either (a) finish it by hand and then `/execute-prp PRPs/v1_{slug}.md --component {name}` to mark it built, or (b) revert the component folder and re-run `/execute-prp`."
- **If all DONE but `.scaffolding/` still present**: "All components are built but `.scaffolding/` wasn't cleaned up — unusual. Re-run `/execute-prp PRPs/v1_{slug}.md` (or manually delete `.scaffolding/`) to finalize."
```

### 4b. Render the built report

If the manifest is absent. The project is built.

```markdown
## **PROJECT READY TO USE: YES**

{project_name (from CLAUDE.md's `# Project:` header) — or the folder name if unreadable}. All v1 components built and validated. Scaffolder state removed.

### How to run

{Entry commands from the "How to run" column of CLAUDE.md's "## Components" index table — one per component}

{If `.env.example` exists, add:}

### Configuration

{n}/{total} secrets set. {If any are unset, list the missing key NAMES and add: "Run `.\scripts\secure\Set-ProjectSecrets.ps1` in your own terminal — not through Claude. Components that need those keys will fail until it's done."}

{If active post-build feature PRPs exist, add an "Active feature PRPs" section:}

### Active feature PRPs

- `PRPs/{slug}.md` — run `/execute-prp PRPs/{slug}.md` to build this feature.

### Next step

{Branches:}

- **If no active feature PRPs**: "Nothing pending. If you want to add a new feature: edit `PRPs/source/INITIAL.md` → `/generate-prp` → `/execute-prp PRPs/<new-slug>.md`."
- **If active feature PRPs exist**: "{count} feature PRP(s) pending. Run `/execute-prp PRPs/<slug>.md` on the one you want to build next."
```

---

## Rendering rules

- Use the emoji symbols (✅ / 🟡 / ⬜) in the State column — they render in Claude Code's terminal and communicate status at a glance. Fall back to text (DONE / IN PROGRESS / INCOMPLETE) if terminal rendering looks broken.
- Keep the report short. Target: under 30 lines for a 3-component project.
- Don't invent fields that aren't in the manifest.
- **Never** suggest running a component's entry command when the project is not READY TO USE. Stubs will error or do nothing useful.
- If the manifest is malformed (fails to parse), show a FAIL header and suggest `git log .scaffolding/manifest.json` to see what was last written, then exit.

---

## Anti-patterns

- Do NOT write to `.scaffolding/manifest.json` — this command is read-only.
- Do NOT re-run `/execute-prp` on your own — just report what the user should do next.
- Do NOT deep-read component source files — peek at the first 30 lines is enough for stub detection.
- Do NOT read `.env`, or work around the deny rules to inspect it. `Test-Readiness.ps1` is the only sanctioned way to learn configuration state, and it reports names only.
- Do NOT run `Set-ProjectSecrets.ps1` — it's interactive, and Claude Code's stdin is the null device, so it would write empty values.
- Do NOT speculate about feature completeness beyond what the manifest + PRP-archive state tell you.

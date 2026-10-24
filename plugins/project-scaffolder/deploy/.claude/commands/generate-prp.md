# Generate PRP

## INITIAL file: $ARGUMENTS

Generate a complete Product Requirements Prompt (PRP) from an INITIAL.md-style feature spec. The PRP becomes the source of truth for implementation — include ALL context the implementation session will need, because that session may not have this conversation available.

**Resolving `$ARGUMENTS`:**
- If no argument was passed, resolve to `PRPs/source/INITIAL.md` — scaffolded projects ship the intake there, and feature edits happen in place.
- If the user passed an explicit path (e.g., `/generate-prp PRPs/source/INITIAL.md` or `/generate-prp PRPs/source/INITIAL_auth.md`), use that path.
- If the user passed `INITIAL.md` and that file doesn't exist at the project root, check `PRPs/source/INITIAL.md` as a fallback (legacy behavior — projects scaffolded before INITIAL shipped in `PRPs/source/` may still have a root file, and users sometimes drop feature-specific `INITIAL_<slug>.md` at the root for the relocation step below to handle).
- If nothing resolves, stop and ask the user which intake file to read.

Read the resolved INITIAL file first. Understand what's being asked, what components exist, what examples are provided, what constraints matter.

---

## Multi-component INITIAL

If `INITIAL.md` has a `## COMPONENTS` section with one or more `### COMPONENT: <name>` blocks (the shape produced by `/new-project`), treat it as a **multi-component project**. Produce **one PRP that covers all components** — not one PRP per component.

The mega-PRP approach keeps the implementation in a single plan with clear ordering, shared context (libraries, doc links, project-wide considerations), and aggregated validation gates. `/execute-prp` can then build the components in the right order in one session or across several.

Components without a `## COMPONENTS` section: treat it as a single feature/project and write a normal PRP.

**Scope note for option-B projects (scaffolded by `/new-project`):** the initial v1 build does NOT use `/generate-prp` — the v1 mega-PRP is written directly at scaffold time to `PRPs/v1_<slug>.md`. Use `/generate-prp` only for **adding features to an already-built project**. If you're here on a fresh scaffold (`.scaffold_manifest.json` shows `lifecycle.stage: "plan"` with all components still `scaffold_state: "stub"`), point the user at `/execute-prp PRPs/v1_<slug>.md` instead and stop.

---

## What kind of work is this?

Read the INITIAL and classify. For a multi-component project, classify each component — the PRP's research section will reflect the union.

| Kind | Signals in INITIAL | Research depth |
| --- | --- | --- |
| **Feature in existing codebase** | References `examples/` files, internal docs, established patterns | Codebase-heavy: study existing patterns, match conventions |
| **New subsystem in this project** | Describes a significant component with its own stack or dependencies | Web research on the stack, then codify patterns in the PRP |
| **Data analysis / research / report** | Describes input data or a question to answer; output is a deliverable | Domain research, data structure exploration, output-format patterns |
| **Tool / automation / integration** | External API involved, scheduled behavior, script-like scope | API docs, rate-limit/error-handling patterns, integration test approach |

Scale research effort to match. Don't over-research simple things.

---

## Research Process

### 1. Codebase Analysis (always)

Since `/generate-prp` is post-build for option-B projects, there IS a real codebase to analyze:

- **Read `components/<name>/CLAUDE.md` for every component this feature touches.** Do this explicitly — those files hold the component's pattern gotchas, and Claude Code only auto-loads them once you read a file inside that folder. During planning you may reason about a component without opening its code, which would skip its rules entirely.
- Search for similar features/patterns already in the project (`components/`, `src/<package>/`, and `PRPs/archive/` — archived PRPs show what patterns worked before)
- Identify files worth referencing in the PRP
- Note existing conventions (naming, structure, testing style)
- Check test patterns so validation gates match what already works
- For multi-component additions: note shared infrastructure that must stay consistent — the root `pyproject.toml` is the only dependency manifest (never add a component-local one), and the root `.env` is the only secrets file. New secrets mean adding key names to `.env.example` and telling the user to run `scripts/secure/Set-ProjectSecrets.ps1`; you cannot read or write `.env` yourself.

### 2. External Research — depth scales with task type

For any task:
- Library/framework documentation for anything used (link specific sections)
- Implementation examples (GitHub, blogs, StackOverflow)
- Best practices and common pitfalls
- Validation/testing tools for the stack

**Framework-template tasks specifically require:**
- Official framework docs read thoroughly, not skimmed
- Real-world implementations studied for patterns
- Gotchas and edge cases documented (community reports, issue trackers)
- Testing frameworks and validation approaches identified
- Security considerations catalogued

Use sub-agents (Explore, general-purpose) when research will generate noise. Keep the main session focused on writing the PRP.

### 3. User clarification (if genuinely needed)

Ask only when the INITIAL leaves critical ambiguity. Prefer making a reasonable default explicit in the PRP over asking.

---

## PRP Generation

Use `PRPs/templates/prp_base.md` as your starting structure. For multi-component INITIAL, organize the PRP as follows:

### PRP structure for multi-component projects

1. **Project overview** — one paragraph from `## PROJECT`
2. **Shared context** — docs, libraries, project-wide gotchas that apply to multiple components (from `## SHARED DOCUMENTATION` and `## OTHER CONSIDERATIONS`)
3. **Component sections** — one per `### COMPONENT:` block in INITIAL:
   - Purpose, inputs, outputs (verbatim from INITIAL)
   - Component-specific research findings (library choices, patterns, gotchas)
   - Component-specific implementation blueprint (ordered tasks, pseudocode, files to create/modify)
   - Component-specific validation gates
4. **Implementation order** — which components to build first based on the data-flow dependencies declared in INITIAL (e.g., "build `refresh_cli` first because `ticket_insights` depends on its output format")
5. **Aggregate validation gates** — commands that verify the whole project works end-to-end (structural checks, all component tests, gitignore respected)
6. **Success criteria** — one checklist covering every component

### What must be in the PRP

- **Context**: URLs with specific sections; internal files with why-to-read; gotchas; patterns; doc fragments pasted where useful
- **Implementation blueprint**: ordered task list per component + inter-component ordering
- **Validation gates** (MUST be executable): per-component + aggregate
- **Error handling patterns**
- **Success criteria** (checklist)

### Output location

| Task kind | Save as |
| --- | --- |
| Multi-component project (from `/new-project`) | `PRPs/<project-slug>.md` — one PRP for the whole project |
| Single feature / analysis / tool | `PRPs/<slug-from-INITIAL>.md` |

---

## Quality

Before finalizing, verify:

- [ ] All necessary context is included (or linked where it exists)
- [ ] Validation gates are executable from the command line
- [ ] References existing codebase patterns where applicable
- [ ] Clear, ordered implementation path (including inter-component ordering for multi-component PRPs)
- [ ] Every component declared in INITIAL has its own section
- [ ] Error handling and edge cases documented
- [ ] Anti-patterns / what-not-to-do section for the tricky parts

Score the PRP 1-10 (confidence in one-pass implementation success). If under 7, research more or ask clarifying questions before saving.

---

## Relocate a root-placed INITIAL (fallback-only)

Scaffolded projects ship `INITIAL.md` at `PRPs/source/INITIAL.md` — this section does nothing in that common case. Only relevant when a user manually drops a feature spec at the project root (e.g., `INITIAL_auth.md`) and wants the root to stay tidy after generation:

```bash
# Only runs if the resolved INITIAL file was at the project root.
if [ -f "INITIAL.md" ]; then
  mkdir -p PRPs/source
  mv INITIAL.md PRPs/source/INITIAL.md
fi
```

Skip this step entirely if the resolved file already lived in `PRPs/source/` or at a path the user typed explicitly.

---

## ULTRATHINK

After research, before writing: pause and plan the PRP structure. Decide what's essential vs. noise. A multi-component PRP that's 3000 lines but mostly filler is worse than 800 lines of dense, relevant context.

For multi-component projects especially: the inter-component ordering matters more than you think. Spend time on the data-flow dependencies before writing the blueprint — getting component order right prevents the executor from needing to backtrack.

The goal: one-pass implementation success through comprehensive, focused context.

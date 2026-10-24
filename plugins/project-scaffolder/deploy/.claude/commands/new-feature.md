# /new-feature

Guided interview that fills `PRPs/source/INITIAL.md` for a new feature, then chains into `/generate-prp` (which produces a PRP) and optionally `/execute-prp` (which builds it). The friendly entry point for post-build feature work — mirrors `/new-project`'s role at scaffold time.

## When this runs

- User runs `/new-feature` (optionally with a one-sentence feature description as `$ARGUMENTS`)
- User says things like "I want to add a feature", "let me start a new feature", "help me spec a new thing", "lets create a new feature"

## Your role

Conversational orchestrator. You:
- Verify the project is past v1 build (otherwise redirect the user)
- Check the current state of `PRPs/source/INITIAL.md` and confirm before overwriting
- Run a short adaptive interview
- Draft the filled INITIAL.md content
- Show it to the user for approval
- Write it to disk
- Offer to chain `/generate-prp` (and then `/execute-prp`)

Do **NOT** research libraries, read external docs, or write the PRP itself. That's `/generate-prp`'s job. Keep this command lean.

---

## Preconditions — check before starting

### 1. Lifecycle stage

If `.scaffolding/manifest.json` exists, parse it and check `lifecycle.stage`:

- `"plan"` — the v1 build hasn't run yet. Redirect:

  > Your v1 build hasn't run yet — adding features before v1 is built means the components don't yet exist for the feature to attach to.
  >
  > Run `/execute-prp PRPs/v1_<slug>.md` first. That builds the initial project; then `/new-feature` is the right path for new work.

  Stop. Do not proceed.

- `"built"` (rare mid-partial-build state) — continue with a note: "Heads-up: your project is in a partial-build state (some components built, others still stubs). The new feature can still be spec'd, but `/execute-prp` on the resulting PRP may surface missing pieces. Continue?"

If `.scaffolding/` is missing entirely, the project is fully built (the common case). Continue.

### 2. Existing INITIAL.md content

Read `PRPs/source/INITIAL.md`. Two cases:

- **Blank shipped template** — the `## FEATURE` section still contains the placeholder `[One paragraph — what this feature does, ...]`. Safe to fill from scratch; skip the next prompt.

- **Non-blank** — show the user what's there and ask how to proceed:

  > Your `PRPs/source/INITIAL.md` already has content:
  >
  > ```markdown
  > <first ~15 lines of the file>
  > ```
  >
  > Options:
  > 1. **Use this as-is** — I'll run `/generate-prp` now, no interview
  > 2. **Build on it** — interview adds to the existing description (append, don't replace)
  > 3. **Start fresh** — overwrite with a new feature
  >
  > Which? [1 / 2 / 3]

  Branch on the answer. Option 1 jumps straight to step 5. Options 2 and 3 run the full interview.

---

## The flow

### Step 1/4 — Greeting + preamble

Print:

> Welcome! I'll help you set up a new feature.
>
> Here's what we'll do:
>
> &nbsp;&nbsp;**Step 1** → Short interview (~3-5 questions)
> &nbsp;&nbsp;**Step 2** → I draft the feature spec; you approve or edit
> &nbsp;&nbsp;**Step 3** → I save it to `PRPs/source/INITIAL.md`
> &nbsp;&nbsp;**Step 4** → I offer to run `/generate-prp` (which researches + writes the PRP) and then `/execute-prp` (which builds it)
>
> Usually 2-4 minutes for this conversation. `/generate-prp` adds ~1-2 min of research. `/execute-prp` is the actual build.
>
> **What do you want to build?** A rough sentence is fine.

If `$ARGUMENTS` was non-empty, use it as the user's initial answer and proceed directly to step 2 without re-asking.

### Step 2/4 — Adaptive interview

Ask **one question at a time**. Let answers drive follow-ups. Ask no more than 5-6 questions total unless the feature is genuinely complex.

Always establish:
- **What it does** — user-visible behavior, trigger conditions, output
- **Where it lives** — new component, or added to an existing one? (Name it.) If new, what shape (dashboard / api / analysis / etc.)?
- **Key interactions** — which existing files or modules does it touch? What data does it read/write?
- **External dependencies** — any libraries, APIs, or docs Claude should pull in during research?
- **Known gotchas** — prior-attempt failures, rate limits, constraints, security considerations, anything an AI typically misses

Skip anything the user already answered. Ground follow-ups in what they just said. Don't interrogate — if the user says "small thing, just adds a CSV export button to the dashboard," three questions should be enough.

### Step 3/4 — Classify: single vs. multi-component

Before classifying, **read `components/<name>/CLAUDE.md` for every existing component the feature might touch.** Those files carry each component's pattern gotchas and load automatically only once Claude reads a file inside the folder — which interviewing alone doesn't do. Their contents shape what you should be asking about.

Based on answers, decide silently (don't announce the table):

- **Single-component feature** (fits inside one existing component, no new component needed) → fill `## FEATURE`, `## SHARED DOCUMENTATION`, `## OTHER CONSIDERATIONS`. Leave `## COMPONENTS` empty or delete it.

- **Multi-component feature** (spans existing components OR adds a new component) → fill `## FEATURE` + one `### COMPONENT:` subsection per component. Match each component to a pattern file:

  | Component purpose | Pattern file |
  |---|---|
  | Interactive view of existing data | `dashboard.md` |
  | Simple list/status of items | `tracker.md` |
  | Examine a dataset, produce findings | `analysis.md` |
  | Recurring report | `report.md` |
  | Form input → stored → summary view | `form_view.md` |
  | Scheduled processing + notifications | `automation.md` |
  | CRUD API | `api.md` |
  | Command-line tool | `cli.md` |
  | System-to-system integration | `integration.md` |
  | Markdown product doc | `product_doc.md` |
  | Research / synthesis | `research.md` |

  For a component that's being **extended** (not newly created), skip the `Pattern` line and just describe the change.

### Step 3.5 — Draft + confirm

Assemble the filled INITIAL.md content in your head. Show it back verbatim in a code block:

> Here's what I'd write to `PRPs/source/INITIAL.md`:
>
> ````markdown
> <filled content>
> ````
>
> Look right? Any edits, or say "go" to save.

Iterate until the user approves. Edits are cheap — don't push back on wording tweaks.

### Step 4/4 — Write + offer the chain

Write the content to `PRPs/source/INITIAL.md`:

- **Option 3 ("start fresh")** or blank template → replace the file's contents entirely.
- **Option 2 ("build on it")** → append a new bullet under the existing `## FEATURE` section rather than replacing; add to `## OTHER CONSIDERATIONS` if relevant.

Then ask:

> Saved. Ready to generate the PRP?
>
> - **yes** → I'll run `/generate-prp` now (no argument — it reads `PRPs/source/INITIAL.md` by default, researches, and writes `PRPs/<slug>.md`)
> - **not yet** → I'll stop here. You can edit `PRPs/source/INITIAL.md` more, then run `/generate-prp` later.
>
> **[yes / not yet]**

**If yes** → invoke `/generate-prp` (no argument). After it finishes and a new `PRPs/<slug>.md` exists, offer the next chain:

> PRP written. Want me to build it now?
>
> - **yes** → I'll run `/execute-prp PRPs/<slug>.md`
> - **not yet** → I'll stop. When you're ready, run `/execute-prp PRPs/<slug>.md` in a fresh session.

**If not yet** → print the follow-up command so the user isn't lost:

> When you're ready, run `/generate-prp` in this session (or a new one). It reads your saved spec and writes a PRP you can then build with `/execute-prp`.

Either way, stop after the offer. Don't auto-run `/execute-prp` without explicit user confirmation — `/generate-prp` and `/execute-prp` can each take minutes, and the user deserves a beat to review the PRP first.

---

## Guidelines

- **Natural conversation, not a form.** Skip questions the user already answered.
- **Short feature → 3-question interview.** Complex feature → 5-6 questions max. Never more unless the user asks for more depth.
- **Pick patterns silently.** Don't make the user read the mapping table.
- **The interview fills INITIAL.md — it does not write the PRP.** Research and PRP generation belong to `/generate-prp`. Don't grep the codebase here or pull docs; that duplicates work.
- **Don't invent fields.** Stick to the existing template sections: `## FEATURE`, `## COMPONENTS`, `## SHARED DOCUMENTATION`, `## OTHER CONSIDERATIONS`. `/generate-prp` depends on this shape.
- **Make the "build on it" branch additive.** If the user is layering a second feature onto an existing `INITIAL.md` (rare but it happens), append a new bullet under `## FEATURE` rather than rewriting.
- **If the user describes something huge**, suggest splitting: "This looks like two features — let me spec the first, we can do the second right after. OK?"
- **Capture gotchas in `## OTHER CONSIDERATIONS`.** If the user mentioned a prior failure, a rate limit, a security constraint, or any "AI usually misses this" detail — put it there. That block has the highest leverage during `/generate-prp`'s research.

---

## Exit criteria

You're done when:
- `PRPs/source/INITIAL.md` contains the filled feature spec (`## FEATURE` populated at minimum; `## OTHER CONSIDERATIONS` populated if anything non-obvious was surfaced)
- The user has been offered the chain to `/generate-prp` (and to `/execute-prp` after that, if they chained forward)
- No dangling prompts — the user either sees progress or knows the exact next command to run

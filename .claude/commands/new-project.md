# /new-project

Guided conversational scaffolder using **parallel sub-agent orchestration**. A scaffolded project is a well-organized workspace containing **one or more components** — each component is a purposeful, named piece of work (an analysis, a CLI, a report, etc.) and maps to a single pattern from `patterns/`.

Use this when the user:
- Runs `/new-project` explicitly
- Says anything like "I want to start a new project," "help me build something," "make me a [thing]"
- Is clearly non-technical and needs help figuring out what they even need

**Your role**: you're the **orchestrator** coordinating specialist sub-agents. You handle the conversation with the user; sub-agents handle research, design synthesis, per-component scaffolding, and validation in isolated context. Never dump technical jargon on the user. If you have to say something technical, briefly explain it in plain language.

---

## Core concept: projects contain components

A project is a named workspace with its own folder structure. Inside it live 1 or more **components** — each component solves one piece of the user's overall goal.

Example: a user says "I want to analyze our support tickets, generate a weekly report, and have a CLI to trigger a refresh." That's one project (`support_workflow`) with three components: `ticket_insights` (analysis), `weekly_report` (report), `refresh_cli` (cli).

Each component maps to one pattern in `patterns/`. Components share the project's `data/` (inputs) and `output/` (artifacts) directories.

---

## The flow — orchestrated sub-agents

```
Greeting → Interview (main session) ─┐
                                     ├─► Decomposition: break into components
                                     ├─► Flow discussion: inputs/outputs per component
                                     ├─► Propose project structure (tree + data flow)
                                     │
                                     ├─► ce-researcher × N components (parallel via Task tool)
                                     │         └─► returns: Research Brief (per component)
                                     │
                                     ├─► ce-planner (after all research returns)
                                     │         └─► returns: Multi-component Design Proposal
                                     │
Design Proposal ← main session shows to user
     │
     └─► User approves / iterates
           │
           ▼
     Scaffold:
       Main session writes project-root files + folder skeleton
       ce-scaffold × N components (parallel via Task tool)
             └─► returns: Component reports (files + gotchas + validation)
           │
           ▼
     Main session builds CLAUDE.md dynamically from component reports
           │
           ▼
     ce-validator (Task tool, post-scaffold)
           └─► returns: Validation Report
     │
     ▼
     Handoff to user
```

**Custom sub-agents** live in `.claude/agents/`:
- `ce-researcher` — web research + pattern extraction + gotcha mining (per component)
- `ce-planner` — synthesizes multi-component design proposal
- `ce-scaffold` — writes one component's folder (per component, parallel)
- `ce-validator` — post-scaffold smoke checks

Dispatch them via the **Task tool**, setting `subagent_type` to the agent name. They run in isolated context with their own tool access; the main session stays clean.

---

### 1. Greeting + "what to expect" preamble

**Open with a warm welcome AND set expectations.** Print this before anything else:

> Welcome! I'll help you set up a new project from scratch.
>
> Here's what we'll do together:
>
> &nbsp;&nbsp;**Step 1** → I ask a few questions to understand your overall goal
> &nbsp;&nbsp;**Step 2** → Quick check: I name the pieces ("components") and you confirm the breakdown
> &nbsp;&nbsp;**Step 3** → I research each component in parallel (~30 seconds; you'll see live progress)
> &nbsp;&nbsp;**Step 4** → I show you one unified design — folder path, components, flow, stack — all at once. You approve or adjust.
> &nbsp;&nbsp;**Step 5** → I create the project folder, then verify everything
> &nbsp;&nbsp;**Step 6** → I offer to launch your new project and kick off the build automatically
>
> Usually takes 4-7 minutes. Two moments where I'll need you (steps 2 and 4); the rest you can watch.
>
> **Prefer to review every piece step by step?** Say "walk me through each step" and I'll switch to fine-grained mode.
>
> **Ready? Tell me — what are you trying to build?** A rough sentence is fine.

Then wait for the user's answer.

---

### 2. Interview — adaptive, conversational

**Announce the step**:

> **Step 1/6 — Understanding your goal**

Do NOT ask all questions upfront. Ask one at a time. Let their answers drive what you ask next. Goal: gather enough to understand what pieces of work exist and how data flows through them.

**Always establish:**
- **What are they trying to accomplish?** (the high-level goal, in their words)
- **Who will use it?** (just them / their team / outside users)
- **What data or systems are involved?** (spreadsheets, APIs, databases, nothing yet)
- **What are the outputs they need?** (a dashboard to click through? a report to send? just a running script?)
- **How often will each piece run?** (one-off, on-demand, scheduled, always-on)

**Ask follow-ups grounded in what they just said.** If their first message already answers multiple questions, skip to the next unknown.

> User: "I want to analyze support tickets and send a weekly summary"
> You: "Got it. Where do the tickets come from — Zendesk, Intercom, a CSV export? And the weekly summary — does it go to an email list, a shared doc, a Slack channel?"

> User: "Something to track our onboarding and let managers leave notes"
> You: "Makes sense. Two questions: how many new hires at once (a few, a dozen, fifty)? And who updates the status — HR, the hires themselves, or managers?"

**If they're unsure** ("I don't know exactly what I need"): ask about the end state. "What would success look like for v1 — what would you be doing with this thing a month from now?"

---

### 3. Component sanity check (light — not an approval ceremony)

**Goal**: catch the rare "I meant 1 component, not 3" before expensive research fires. NOT a stop-and-approve moment; aim for under 10 seconds of user attention.

**Announce briefly**:

> **Step 2/6 — Component breakdown**

**Break the user's intent into 1-N components silently** (each purposeful, snake_case-named, mapped to one pattern from `patterns/`). Then show a one-line sanity check:

> I'll set this up as **3 components**: `ticket_insights` (pattern analysis), `weekly_report` (recurring report), `refresh_cli` (CLI tool).
>
> Sound right, or want a different breakdown?

If the user replies "yes" / "looks good" / "go" / silence-after-beat → proceed to step 4 (classification is already done internally). If they want changes → iterate once, then proceed.

**Do NOT** show per-component descriptions, flow arrows, or folder trees here. Those all consolidate into step 9's unified proposal. This is just a component-count + naming check.

**Name suggestions — guidelines (apply silently when proposing):**
- snake_case, short, descriptive
- Nouns for things that produce artifacts (`weekly_report`, `customer_summary`)
- Verbs or verb+noun for tools that do things (`refresh_cli`, `send_digest`)

**Edge cases (handle in the one-line sanity check, not a separate conversation):**
- **User describes one thing**: still use `components/<name>/` for consistency. Say "1 component: `<name>`" — no defense needed.
- **User describes something huge**: push back before the sanity check. "This sounds like multiple projects — let me scope v1 to [X] and we can add more later. OK?" Only show the sanity check once the scope is reasonable.
- **Two "components" are really one thing**: merge silently. Don't surface the internal debate to the user.

**Escape hatch**: if the user signaled in step 1 ("walk me through each step"), revert to the old-style expanded proposal with per-component descriptions, flow discussion as a separate step, structure approval as a separate step, etc. See Guidelines below.

---

### 4. Classify each component to a pattern

**Quietly** (don't announce the table) — for each component, pick one pattern file:

| Component purpose | Pattern file | Default stack |
|---|---|---|
| Interactive view of existing data | `patterns/dashboard.md` | Python + Streamlit |
| Simple list/status of items | `patterns/tracker.md` | Python + markdown files |
| Gather info, synthesize, deliver a written report | `patterns/research.md` | Markdown-based research workflow, no code needed |
| Examine a dataset, produce findings | `patterns/analysis.md` | Python + pandas |
| Recurring report combining data + narrative (weekly/monthly/exec summary) | `patterns/report.md` | Python + pandas + Jinja2 |
| PRD, one-pager, launch brief, product doc | `patterns/product_doc.md` | Markdown (+ optional pandoc for PDF) |
| Form input → stored → summary view | `patterns/form_view.md` | Python + FastAPI + Jinja / Streamlit |
| Runs on a schedule, processes things, notifies | `patterns/automation.md` | Python script + cron |
| CRUD API with auth | `patterns/api.md` | Python + FastAPI + SQLAlchemy |
| Command-line tool | `patterns/cli.md` | Python + click / Typer |
| System-to-system integration | `patterns/integration.md` | Python + requests + SQLAlchemy |

Read each matching `patterns/<shape>.md` to understand its default stack, folder conventions, and I/O expectations.

---

### 5. Work out flow and structure silently (no user approval yet)

**Don't announce this step** — it happens internally between the component sanity check and the research dispatch. The user sees no output here.

Do this work:

1. **Determine each component's inputs and outputs.** For each component, what data sources does it read from (`data/<source>/`) and where do its artifacts land (`output/<component>/<YYYY-MM-DD>_<run>/`)? Infer from the interview — if the user said "I want Monday reports from the ticket data," the flow is obvious. Ask only if a component's I/O is genuinely ambiguous after the interview (rare).
2. **Decide the folder structure.** Canonical: `components/`, `data/<source>/`, `output/<component>/`, `PRPs/`, `.claude/`, plus the `data/<source>/` subfolders for declared sources and `output/<component>/` subfolders for producing components.

**Conventions (apply silently):**
- Output: `output/<component_name>/<YYYY-MM-DD>_<run_description>/` — date first, never overwrite.
- Input: `data/<source_name>/` — one subfolder per external source, named by the source.
- Every component that produces artifacts has a dedicated output folder.

**The user will see all of this once, unified, in step 9** (design proposal). Don't surface it piecemeal here — that's the whole point of the consolidation.

**Escape hatch**: if the user asked for step-by-step mode in step 1, revert to the old per-step surfacing — announce "Now let's map how data flows," show flow arrows, get approval; then announce structure proposal, show tree, get approval. See Guidelines.

---

### 7. Dispatch ce-researcher per component (parallel)

**Announce with per-component scope** (not a generic "I'll work quietly"). Tell the user exactly what's being researched for which component so the wait feels purposeful:

> **Step 3/6 — Researching each component** *(back in ~30 seconds)*
>
> - `<component_1>` → researching <stack/framework from pattern + any user-named specifics>
> - `<component_2>` → researching <...>
> - `<component_3>` → researching <...>

Worked example for a 3-component project:

> **Step 3/6 — Researching each component** *(back in ~30 seconds)*
>
> - `ticket_insights` → researching pandas + data analysis gotchas
> - `weekly_report` → researching Jinja2 templates + recurring-report patterns
> - `refresh_cli` → researching click + Zendesk API idioms

**For each component, dispatch ce-researcher via Task tool.** All dispatches in a single message so they run in parallel.

Example invocation pattern (you, the orchestrator, decide prompts per component):

> Task tool, `subagent_type: "ce-researcher"`, one call per component:
>
> ```
> User intent: <1-3 sentence summary of this specific component>
> Shape classification: patterns/analysis.md
> Specific framework/stack: pandas
> Depth: light
>
> Confirm pattern defaults or recommend deviations. Return a Research Brief.
> ```

**Depth guidance (decide per component):**
- **Light** — well-known pattern, no specific framework named → confirm defaults
- **Medium** — user named a specific framework with real gotchas → pull in docs for the tricky bits
- **Heavy** — user named a framework with significant version/idiom churn or a niche domain → deeper docs pass (rare)

**Skip research entirely** for components where the pattern file fully covers it (e.g., `research.md`, `product_doc.md` for simple cases). Just note "pattern defaults apply" for that component.

**After all researchers return**, print a per-component summary (one salient finding each — pick from each brief's top `## Key patterns to follow` bullet or the stack-recommendation line, whichever is more informative for that component):

> Research complete:
>
> - `ticket_insights`: pandas 2.2; fiscal-year handling flagged
> - `weekly_report`: Jinja2 + date-stamped output folders; TL;DR-first layout
> - `refresh_cli`: click 8 + httpx; rate-limit backoff pattern confirmed
>
> Synthesizing the full design now...

Keep each line under ~70 characters. If a research brief says "pattern defaults apply, no additional research needed," surface that component as `<name>: pattern defaults` — don't fabricate findings.

---

### 8. Dispatch ce-planner

**Announce**:

> **Step 4/6 — Putting the design together**

Dispatch ce-planner via Task tool once with the full multi-component spec:

> Task tool, `subagent_type: "ce-planner"`, prompt:
>
> ```
> Project name: <slug>
> Overall goal: <one paragraph from interview>
>
> Components:
> 1. <name> — pattern: <file> — purpose: <...> — inputs: <...> — outputs: <...> — research brief: <from ce-researcher or "pattern defaults apply">
> 2. <name> — ...
> 3. <name> — ...
>
> Data flow: <the arrows from Step 5>
>
> Produce a user-facing multi-component design proposal.
> ```

ce-planner returns a proposal in plain language. Show it to the user essentially verbatim.

---

### 9. Unified proposal + iteration (the single big approval moment)

**Pre-compute the target path** before showing the proposal. Default: `~/projects/<slugified-project-name>`. Expand `~` to the user's home directory. No separate ask — the path is part of the proposal and the user can change it during iteration.

**Show ce-planner's proposal verbatim, preceded by a target-path line.** The user sees one block with: target path + description + components + flow + stack + any extra top-level folders. Example shape:

> I'd create **`support_workflow`** at `~/projects/support_workflow`. (Want a different location? Tell me during review.)
>
> <ce-planner output here — components bullets + data-flow sentence + stack + optional "Extra top-level folders" block + the "Anything you'd change?" closer>

**Iteration handling.** User's response routes to one of:

- *"Looks good"* / *"go"* / silence-after-beat → approve the full design. Lock in: component list, flow, stack, `project_level_folders` (possibly empty), and target path.
- *"Change the path to X"* → update target path, keep everything else.
- *"Skip `<folder>/`"* / *"drop templates/"* → remove from `project_level_folders`.
- *"Also add `<folder>/`"* → accept user-added folders. If they provide a purpose, use it; otherwise use `"Added by user — edit this README to describe what goes here."`
- *"Rename `<component>` to `<name>`"* → rename. If the rename changes a pattern (rare), re-dispatch ce-researcher for just that component.
- *"I need a different stack for `<component>`"* → honor the ask. Re-dispatch ce-researcher for that component if it's a meaningful shift.
- Major restructuring → re-run ce-planner with the updated spec, show the new proposal.

Keep iterating until the user says "go" (or equivalent). When they do, proceed to scaffold.

---

### 10. Scaffold

**Announce**:

> **Step 5/6 — Creating your project**
>
> Here's what I'm about to do:

Print a scaffolding manifest BEFORE files appear:

> ```
> Creating folder:           <target path>
>   ├─ .scaffolding/           (transient scaffolder state + first-run notes — auto-deleted by /execute-prp on successful build)
>   │    └─ README.md         (what's done + what's next + newcomer tips)
>   ├─ CLAUDE.md              (rules for Claude — includes your project structure + component gotchas)
>   ├─ README.md              (one-page overview)
>   ├─ PRPs/                  (where future plans will live)
>   │    └─ source/
>   │         └─ INITIAL.md   (pre-filled intent — one block per component; edit for new features)
>   ├─ .claude/
>   │    ├─ settings.local.json    (permissions)
>   │    └─ commands/              (/new-feature, /generate-prp, /execute-prp, /handoff)
>   ├─ components/
>   │    ├─ <component_1>/
>   │    ├─ <component_2>/
>   │    └─ <component_3>/
>   ├─ data/
>   │    └─ <source>/           (for your inputs)
>   ├─ output/
>   │    ├─ <component_1>/      (for its artifacts)
>   │    └─ <component_2>/
>   └─ .gitignore             (ready if you choose to `git init` later — optional)
> ```
>
> *(If the user approved any `project_level_folders` during design iteration, add one line per folder before the `.gitignore` line — e.g., `>   ├─ notebooks/             (exploratory hypothesis-testing outside the analysis pipeline)`. Omit entirely if the list is empty.)*
>
> Writing files now...

#### 11a. Main session writes the project-root skeleton

All sourced from **`deploy/`** unless noted. Treat `deploy/` as the canonical template; files outside `deploy/` stay in the kit.

1. **Create the target directory** and the folder skeleton:
   - `components/` (empty — ce-scaffold will fill per component)
   - `data/<source>/` for each declared input source — inside, write a one-line `README.md` (not `.gitkeep`):
     ```
     # <source> inputs

     Drop <source> files here. Consumed by: <comma-separated list of components that read this source>.
     ```
   - `output/<component>/` for each component that produces artifacts — inside, write a one-line `README.md`:
     ```
     # <component> outputs

     Run artifacts from the `<component>` component land here as `<YYYY-MM-DD>_<run-description>/` subfolders. Keep latest ~5; move older to `_archive/`.
     ```
   - `PRPs/`
   - `PRPs/archive/` (with `.gitkeep`) — `/execute-prp` moves completed PRPs here on success
   - `PRPs/source/` — holds `INITIAL.md` (written in item 7 below), so no `.gitkeep` is needed

2. **`.claude/settings.local.json`** — copy from `deploy/.claude/settings.local.json`.

3. **`.claude/commands/`** — copy all from `deploy/.claude/commands/` (`new-feature.md`, `generate-prp.md`, `execute-prp.md`, `handoff.md`).

4. **`.gitignore`** — copy from `deploy/.gitignore`.

5. **`PRPs/templates/prp_base.md`** + **`PRPs/README.md`** — copy both from `deploy/PRPs/`.

6. **`PRPs/source/INITIAL.md`** — copy `deploy/INITIAL.md` as-is (blank template). In the option-B flow, `INITIAL.md` is the **per-feature intake for post-build feature work**, not the scaffold spec — so it ships empty, waiting for the user's next feature idea. The v1 implementation plan is written directly to `PRPs/v1_<project_slug>.md` in step 11d below, not funneled through INITIAL.md.

7. **`README.md`** — a SHORT project README (one page max):
   - **Status banner block at the very top**, delimited by HTML comment markers `<!-- status:begin -->` / `<!-- status:end -->` so `/execute-prp` can rewrite the banner cleanly when the build completes. Default (plan stage — scaffold just finished, PRP already written) text:
     ```markdown
     <!-- status:begin -->
     > **Status: Planned — implementation plan ready at `PRPs/v1_<slug>.md`.**
     > Next step: run `/execute-prp PRPs/v1_<slug>.md` in Claude Code to build the components.
     <!-- status:end -->
     ```
     `/execute-prp` replaces the block contents with the "built" banner on first successful full build. Substitute the actual slug.
   - Project title + one-paragraph description
   - "Project structure" — copy the tree you showed in Step 6
   - "Components" — one line per component: name → purpose → pattern
   - "How to run" — the entry command per component (e.g., `streamlit run components/<name>/app.py`, `python components/<name>/scripts/run.py`)
   - "How to develop with Claude" — brief pointer for the initial build (`/execute-prp PRPs/v1_<slug>.md`) AND for adding features after build (`/new-feature` for the guided path, or manually edit `PRPs/source/INITIAL.md` → `/generate-prp` → `/execute-prp PRPs/<slug>.md`)
   - "How to reopen this project in Claude Code" — one line: `cd <project path> && claude` (no launcher scripts ship)
   - One line at the top directing newcomers to `.scaffolding/README.md` for first-time setup (mention it will be auto-deleted by `/execute-prp` on successful build)

8. **Project-level folders approved during design iteration.** For each entry in `project_level_folders` (may be empty):
   - Create `<project_root>/<folder_name>/`
   - Write `<project_root>/<folder_name>/README.md` with shape:
     ```
     # <folder_name>

     <purpose line from the approved suggestion>
     ```
   Same one-line-README convention as `data/<source>/README.md` and `output/<component>/README.md`. If the user added a folder during iteration without providing a purpose, use `Added by user — edit this README to describe what goes here.` as the purpose line.

**Do NOT run `git init`.** The user might not want version control in this folder, or might plan to place it inside an existing repo. `.scaffolding/README.md` surfaces `git init` as one optional setup item — the user decides.

#### 11b. Dispatch ce-scaffold per component (parallel)

For each component, dispatch ce-scaffold via Task tool — all in a single message so they run in parallel:

> Task tool, `subagent_type: "ce-scaffold"`, one call per component:
>
> ```
> project_root: <absolute target path>
> component_name: <snake_case name>
> pattern_file: <absolute path to patterns/<shape>.md>
> purpose: <one-paragraph description>
> inputs: <declared input path(s) or "none">
> outputs: <declared output path>
> project_stack: <primary language — e.g., "Python 3.11">
> ```

Each ce-scaffold instance writes `components/<name>/` in isolation and returns:
- Files it created
- Gotchas from the pattern (for aggregation into project CLAUDE.md)
- Validation commands for this component
- **First-run setup commands** (install deps, copy `.env.example`) — aggregated into `.scaffolding/README.md`'s Optional setup list
- Any flags for shared dependencies

#### 11c. Build project CLAUDE.md, the .scaffolding/ manifest + README, dynamically

After all ce-scaffold reports return, **you** (main session) write the project's `CLAUDE.md` by assembling:

```markdown
# Project: <Project Name>

<one-paragraph plain-language description>

**Stack**: <languages/frameworks used across components>

---

## Project structure (STRICT — do not deviate)

```
<the tree from Step 6, verbatim>
```

**Enforcement rules:**
- Components live in `components/<name>/` only — never loose at project root
- All inputs live in `data/<source>/` — never inside a component folder
- All outputs land in `output/<component>/<YYYY-MM-DD>_<description>/` — never at project root, never overwriting prior runs
- Never add a new top-level folder without updating this section first
- Never rename `components/`, `data/`, `output/`, or `PRPs/`
{If `project_level_folders` is non-empty, inject an extra bullet here listing each one by name with its purpose — e.g., `- Project-level folders \`notebooks/\` (exploratory hypothesis-testing) and \`templates/\` (shared report layouts) are part of this project's declared structure — use each as described in its README; don't improvise alternatives.` Omit this bullet entirely if no extras were approved.}

---

## Components

### <component_1> (<pattern_name>)

**Purpose**: <one paragraph>
**Inputs**: <declared input paths, or "None">
**Outputs**: <declared output path, or "None">
**How to run**: <the one command>

**Gotchas:**
<bullet list from ce-scaffold's return report for this component>

### <component_2> (<pattern_name>)

...

### <component_3> (<pattern_name>)

...

---

## Validation gates

```bash
<aggregated validation commands from every component's ce-scaffold return>
```

---

<then append deploy/CLAUDE.md verbatim — the generic Session Start / Context Discipline / Code / Testing / Docs / AI Behavior / Project Cleanliness / Task Completion sections>
```

**Why this structure:** the project-specific enforcement rules and per-component gotchas sit at the TOP. Claude reads these first and knows the structural contract before falling through to generic defaults.

**Then write `.scaffolding/manifest.json`**. The `.scaffolding/` folder is the sole location for all transient scaffolder state — it will be auto-deleted by `/execute-prp` on successful v1 build, leaving no scaffolder footprint in the finished project. The manifest is the authoritative status source during the plan → built transition. Shape:

```json
{
  "scaffold_version": 1,
  "scaffolded_at": "<ISO-8601 date, e.g., 2026-04-24>",
  "scaffolder": "claude-project-scaffolder /new-project",
  "project_name": "<Human-readable project name>",
  "project_slug": "<folder name, e.g., TMOS_Strategy_Lab>",
  "stack": "<primary language/runtime, e.g., Python 3.11+>",
  "requirements_doc": "<relative path if the user wrote a spec before scaffolding, e.g., REQUIREMENTS.md — omit the field if no such doc exists>",
  "lifecycle": {
    "stage": "plan",
    "history": [
      {"stage": "plan", "at": "<ISO-8601 date>", "by": "/new-project"}
    ]
  },
  "components": [
    {
      "name": "<component_name>",
      "pattern": "<pattern filename, e.g., cli.md>",
      "purpose_one_line": "<one sentence, lowercase>",
      "inputs": ["<declared input path, e.g., data/rom/>", "..."],
      "outputs": ["<declared output path, e.g., output/<name>/<YYYY-MM-DD>_<desc>/>"],
      "entry_command": "<the one command from CLAUDE.md's How to run>",
      "scaffold_state": "stub",
      "first_run_setup": ["<line from ce-scaffold's first_run_setup return>", "..."]
    }
  ],
  "data_sources": [
    {"name": "<source_name>", "purpose": "<line from data/<source>/README.md>"}
  ],
  "project_level_folders": [
    {"name": "<folder>", "purpose": "<purpose line approved during design iteration>"}
  ],
  "notes_for_generate_prp": "Initial build does NOT use /generate-prp — the v1 PRP was written directly by /new-project at PRPs/v1_<slug>.md. /generate-prp only runs post-build for new features (via PRPs/source/INITIAL.md). After /execute-prp has built real code, this manifest's scaffold_state values are stale — use it only as a project map, not a ground-truth inspector."
}
```

Assembly rules for the manifest:
- `lifecycle.stage` is `"plan"` at `/new-project` time — the PRP is written at scaffold time (step 11d), so the project goes straight to plan stage. `/execute-prp` advances it to `"built"` on first successful full build AND flips every component's `scaffold_state` from `"stub"` to `"built"` at the same time. Each stage transition appends a `{stage, at, by}` entry to `lifecycle.history`. Two stages total — `"scaffold"` is not an observable state in the option-B flow.
- `scaffold_state` at the component level is `"stub"` at scaffold time and only flips to `"built"` inside `/execute-prp` when that component's section of the PRP passes validation. It exists separately from `lifecycle.stage` so `/execute-prp --component <name>` (partial builds) can reflect per-component build state while the project-level stage stays at `"plan"` until ALL components are built.
- `entry_command` comes from the `**How to run**` line in the component's CLAUDE.md section.
- `first_run_setup` is the deduplicated aggregation of every ce-scaffold's `first_run_setup` lines for that component (the same lines that feed `.scaffolding/README.md`).
- `requirements_doc` is present only when the user scaffolded around an existing spec (e.g., the user ran `/new-project` pointing at a pre-written `REQUIREMENTS.md`). Otherwise omit the field.
- `data_sources` and `project_level_folders` carry the same data that went into the per-folder one-line READMEs.
- Do NOT pretty-print with tabs — two-space indent for readability; the file will rarely be read by humans directly.

Then write `.scaffolding/README.md`. This is the first-run onboarding doc — lives alongside the manifest in the `.scaffolding/` folder, and will be auto-deleted with the rest of `.scaffolding/` on first successful `/execute-prp`. Shape:

```markdown
# First-run notes — <Project Name>

Welcome. This folder has everything you need for your first session — the manifest tracking scaffold state, these notes, and the auto-chain helper script (if you chose auto-chain during scaffolding). **`/execute-prp` will delete this whole folder automatically on a successful v1 build** — you don't need to clean anything up. If you'd rather not wait, nothing outside this folder depends on anything inside it; safe to delete early.

## The two stages of your project

Your project is in stage 1 of two. Each stage produces something different:

1. **Plan** *(just finished)* — folder structure, rules in `CLAUDE.md`, starter skeletons in each `components/<name>/`, and the implementation blueprint at `PRPs/v1_<slug>.md`. The skeletons don't do useful work yet; they're the shape the real code gets built into. The PRP is the step-by-step build plan.
2. **Build** *(next — `/execute-prp PRPs/v1_<slug>.md`)* — Claude works the plan step by step, filling in the skeletons with real working code and passing validation gates along the way.

After the v1 build is done, adding new features is easiest via `/new-feature` — a guided interview that fills `PRPs/source/INITIAL.md` for you and chains into `/generate-prp` and `/execute-prp`. You can also do it manually: edit `PRPs/source/INITIAL.md` (the per-feature intake template), run `/generate-prp`, run `/execute-prp PRPs/<new-slug>.md`.

## First time with Claude Code? (skip if you're comfortable)

A few things that catch newcomers off guard — none are problems:

- **Permission prompts are normal.** When `/execute-prp` runs shell commands (install deps, run tests), Claude Code asks before each one. Approve the ones you expect; deny anything surprising. You're always in control.
- **Nothing is destructive by default.** Claude won't delete or force-push. If an edit looks wrong, hit escape and redirect.
- **Need to stop mid-work?** Run `/handoff` — Claude writes a `HANDOFF.md` summarizing state. Next session starts by reading it and picks up where you left off.
- **`/execute-prp` failed partway?** Safe to re-run. The PRP stays in `PRPs/<slug>.md` (not archived) until all validation passes, so resuming just continues from where it stopped.
- **Glossary:** _component_ = a named piece of work; _pattern_ = the shape/stack behind it (dashboard, cli, etc.); _PRP_ = the detailed implementation plan Claude generates; _INITIAL.md_ = your spec that drives the PRP.

## What was set up for you

- Folder structure: `components/` (<N> component folders), `data/<source>/`, `output/<component>/`, `PRPs/`
- `PRPs/v1_<slug>.md` — the implementation plan for your v1 build, written by `/new-project` from the interview + research. Read it if you want; `/execute-prp` will follow it step by step.
- `PRPs/source/INITIAL.md` — blank template for post-build feature work (ignore until v1 is built)
- `CLAUDE.md` — project rules + per-component gotchas (auto-loaded every Claude Code session)
- `README.md` — one-page overview
- `.claude/` — permissions and the four slash commands: `/new-feature`, `/generate-prp`, `/execute-prp`, `/handoff`
- `.gitignore` — ready if you want to use git (no repo initialized — see optional setup below)

## Build your project (inside Claude Code)

1. Open a terminal and run: `cd <project path> && claude`
2. *(Optional)* Skim `PRPs/v1_<slug>.md` to see what Claude plans to build
3. Type `/execute-prp PRPs/v1_<slug>.md` — Claude builds the components and runs validation gates

That's it — one command to go from scaffold to working v1.

## Optional setup

Pick what applies — none of these are required to start building.

<aggregated first_run_setup lines from ce-scaffold reports, deduplicated, one bullet each — e.g.:>
- [ ] `pip install -r components/<name>/requirements.txt`
- [ ] `cp components/<name>/.env.example components/<name>/.env` — then fill in secrets
- [ ] Want version control? `git init && git add . && git commit -m "Initial scaffold"`
<omit the entire section if there are no ce-scaffold setup items AND the user explicitly said they don't use git during the interview; otherwise always include the git bullet last>

## Where to learn more

- `../CLAUDE.md` — rules Claude follows in this project
- `../PRPs/README.md` — how the PRP workflow works end to end
- `../components/<name>/README.md` — per-component orientation

## Cleanup

Automatic — on a successful `/execute-prp PRPs/v1_<slug>.md` run, this whole folder is deleted along with the status banner in `../README.md`. No action needed.
```

**Assembly rules for `.scaffolding/README.md`:**

- Target length: ~45-55 lines. If it's longer, compress.
- "The two stages" block stays first — this is the main orientation most new users need.
- "What was set up" is mostly static — only the component-count hint and the v1 PRP slug vary. Never claim a git repo exists (the scaffolder doesn't create one).
- "Optional setup" aggregates `first_run_setup` lists from every ce-scaffold return, deduplicated verbatim. Put stack-specific items (pip install, env copy) first; the git bullet last so users who don't use git can ignore the whole section cleanly.
- Do NOT include stack conjecture — only emit setup items ce-scaffold explicitly returned.
- Framing matters: "optional" not "required." A user should feel comfortable skipping git entirely.
- Keep the "Done with setup?" block — it's the explicit signal that the folder is safe to delete.
- Paths in the "Where to learn more" section are written relative to `.scaffolding/` (so prefix them with `../`).

After both files are written, print:

> All files created.

#### 11d. Write the v1 mega-PRP inline

**You** (main session) now synthesize `PRPs/v1_<project_slug>.md` directly — no intermediate INITIAL.md, no `/generate-prp` step. You already have every piece of context needed: the user interview, ce-researcher briefs per component, ce-scaffold returns (stub files + gotchas + validation commands + first_run_setup), the design proposal, data flow, build order rationale, and (if present) the user's pre-written `REQUIREMENTS.md`.

Follow the shape of `PRPs/templates/prp_base.md` adapted for multi-component scope. Target ≤ 800 lines — if heading longer, you're duplicating CLAUDE.md content; cite instead of inline.

Required sections in order:

1. **Header** — `name:` line, `description:` block ending with both invocations: `/execute-prp PRPs/v1_<slug>.md` (full build) and `/execute-prp PRPs/v1_<slug>.md --component <name>` (per-component partial build).
2. **Goal / Why / What / Success Criteria** — overall goal restated as target end-state; business value; user-visible behavior; `- [ ]` checklist (one item per component + one item per REQUIREMENTS.md v1-milestone checkbox if present).
3. **All Needed Context**:
   - `Documentation & References` yaml block — shared entries (CLAUDE.md, REQUIREMENTS.md if present) + per-component URLs pulled from each research brief's "Documentation links" section.
   - `Current Codebase tree` — the post-scaffold shape (components as stubs).
   - `Desired Codebase tree` — annotated with files `/execute-prp` will produce, per component.
   - `Known Gotchas` — one code block per component from its research_brief "Gotchas" + ce-scaffold gotchas, deduplicated; plus one block of project-wide invariants (determinism, no-silent-failures, reuse-don't-fork rules — from REQUIREMENTS.md §6 or equivalent).
4. **Implementation Blueprint**:
   - `Shared infrastructure (build first)` — if a `src/<package>/` project-level folder exists, spec its public surface (the types/classes every component imports).
   - Per-component section: `Component: <name> (<pattern>)` → Purpose, Inputs, Outputs, Entry command, Tasks yaml block (in order, MODIFY/CREATE notes referencing stub file paths), Pseudocode blocks with CRITICAL/PATTERN/GOTCHA markers, Component-specific validation bash block.
   - `Build order` — one paragraph based on data-flow dependencies + shared-lib-first rule.
5. **Validation Loop** — three levels:
   - Level 1: project-wide lint + typecheck (ruff, mypy across components + src + tests)
   - Level 2: per-component unit tests (aggregated from each component's validation_commands)
   - Level 3: integration smoke — one or two commands exercising end-to-end data flow
6. **Final Validation Checklist** — `- [ ]` items: lint clean, typecheck clean, every entry command runs, end-to-end smoke produces artifacts, one item per REQUIREMENTS.md v1 milestone check (if present), manifest flipped to `built`.
7. **Anti-Patterns** — top 3-5 from aggregated gotchas.
8. **Context pointers** — cite `CLAUDE.md`, `REQUIREMENTS.md` (if present), per-component READMEs, `PRPs/README.md`.

Write the file. Then print:

> PRP written: `PRPs/v1_<project_slug>.md` (<rough line count> lines). Ready for `/execute-prp`.

**Why inline and not a sub-agent**: the main session already has every piece of context from the interview through the scaffold returns. Dispatching a sub-agent would require re-briefing it with all that context — more tokens, not fewer. Main session writing inline is the simpler path.

---

### 12. Dispatch ce-validator

**Announce** (fold under step 5 — verification is the tail end of "create", not a separate user-facing step):

> Verifying everything looks good...

Dispatch ce-validator via Task tool:

> Task tool, `subagent_type: "ce-validator"`, prompt:
>
> ```
> project_root: <absolute target path>
> components:
>   - name: <component_1>, pattern: <file>, expected_entry: <command>
>   - name: <component_2>, pattern: <file>, expected_entry: <command>
>   - ...
> declared_inputs: <list of data/<source>/ folders>
> declared_outputs: <list of output/<component>/ folders>
> project_level_folders: <list of {name, purpose} for approved extras, or empty list>
> stack: <project stack>
>
> Run validation and return a report.
> ```

Based on result:
- **PASS** → proceed to handoff
- **WARN** → minor issue. Either quickly patch before handoff OR mention to user ("I noticed X; it's minor, fix it in your first session")
- **FAIL** → blocker. Address, re-run validator.

---

### 13. Handoff — offer auto-chain or hand off cleanly

**Announce**:

> **Step 6/6 — Ready to go!**

**Ask the auto-chain question** first (don't dump OS-specific instructions yet):

> Your project is ready at `<target path>`. The implementation plan is already written at `PRPs/v1_<slug>.md`.
>
> **Ready to build?** I can launch your new project and kick off `/execute-prp PRPs/v1_<slug>.md` automatically — Claude will fill in the stubs with real code and run validation gates. Or say "not yet" if you want to review the scaffold + PRP first.
>
> **[yes / not yet]**

**If the user says yes** (auto-chain path):

1. Detect OS (reuse the `uname -s` detection from step 11a).
2. Write a one-time helper script inside `.scaffolding/` (the folder you already created in step 11c). The script cd's to the parent (project root) before launching Claude Code, and deletes only itself on exit — the `.scaffolding/README.md` stays so the user can read it during their first session:
   - **macOS / Linux** — `<target>/.scaffolding/start.sh`:
     ```bash
     #!/usr/bin/env bash
     # One-time auto-chain helper — deletes itself after launching.
     cd "$(dirname "$0")/.."
     trap 'rm -- "$0"' EXIT
     exec claude "/execute-prp PRPs/v1_<slug>.md"
     ```
     `chmod +x` it. Substitute the actual slug.
   - **Windows** — `<target>\.scaffolding\start.bat`:
     ```batch
     @echo off
     cd /d "%~dp0..\"
     claude "/execute-prp PRPs/v1_<slug>.md"
     del "%~f0"
     ```
     Substitute the actual slug.
3. Launch it in the background from the orchestrator session (reuse the OS detection):
   - **macOS**: `open -a Terminal <target>/.scaffolding/start.sh &`
   - **Linux**: `(x-terminal-emulator -e "<target>/.scaffolding/start.sh" &) 2>/dev/null || (gnome-terminal -- "<target>/.scaffolding/start.sh" &) 2>/dev/null || true`
   - **Windows**: `start "" cmd /c "<target>\\.scaffolding\\start.bat"`
4. Print confirmation with direct, step-by-step manual fallback:

   > Launching... a new terminal window should open with `/execute-prp PRPs/v1_<slug>.md` already running in your new project.
   >
   > **If the new window doesn't appear within ~5 seconds**, do this instead:
   >
   > 1. Open a terminal and run: `cd <target path> && claude`
   > 2. When Claude Code opens, type `/execute-prp PRPs/v1_<slug>.md` and press Enter.
   >
   > **Heads-up:** I created a hidden folder called `.scaffolding/` inside your project. It contains the scaffold manifest, first-run notes, and optional setup steps (install deps, copy `.env`, `git init`). **`/execute-prp` will delete this folder automatically when the v1 build succeeds** — leaving your project clean and ready for real work. Read `.scaffolding/README.md` if you want the extra context first.

**If the user says "not yet"** (manual path):

Show direct, step-by-step instructions — not "open this file and read it":

> Your project is ready at `<target path>`. When you're ready to build, do these two things:
>
> 1. **Open Claude Code in the project folder.** Open a terminal and run: `cd <target path> && claude`
> 2. **Type `/execute-prp PRPs/v1_<slug>.md`** and press Enter. Claude reads the v1 implementation plan I already wrote, fills in the stubs with real working code, and runs validation gates.
>
> That's it — one command to go from scaffold to working v1.
>
> **About the hidden `.scaffolding/` folder I created:** it holds the scaffold manifest + first-run notes + optional setup steps. `/execute-prp` deletes it automatically on successful v1 build — your project ends up clean, no scaffolder footprint left behind. Read `.scaffolding/README.md` if you want the extra context first.
>
> `CLAUDE.md` auto-loads every session and tells Claude the rules for this project. You don't need to read it — it's for Claude.

**Either path**: your job ends here. Do NOT run anything else in the orchestrator session.

---

## If the user wants a reusable framework template (rare)

If a developer explicitly asks for a *reusable context-engineering template* for a framework (not a project that uses it), that's outside `/new-project`'s scope. Point them to `use-cases/template-generator/` in the kit — the upstream meta-generator flow — and exit. If they just want to build something that uses a specific framework, stay in `/new-project` and research the framework during the normal research step.

---

## Research/analysis route

If the user wants **pure knowledge work** — one or more research components, no code — you still use the component model:

- Component pattern is `patterns/research.md` or `patterns/product_doc.md`
- No `.py` files inside the component — just markdown templates
- `data/<source>/` holds reference material they want to synthesize from
- `output/<component>/<date>_<run>/` holds deliverables
- PRP workflow still ships (they can use `/generate-prp` for the research plan itself)

---

## Guidelines

- **Natural conversation, not forms.** If their first message already answers multiple questions, skip to the next unknown.
- **Explain technical choices briefly.** "I'll use Streamlit — simplest way to get a dashboard running locally" is fine.
- **Offer defaults, don't demand decisions.** "I'll use markdown unless you want a database — want to stick with markdown?" beats "markdown or SQLite or Postgres?"
- **Propose, don't present options.** Pick what's best; let the user redirect.
- **When in doubt, pick the simplest option.** Streamlit over React. SQLite over Postgres. Markdown over database.
- **Always end with a clear handoff.** They should know exactly what command to run next.
- **Use `components/<name>/` even for one-component projects.** Consistency matters more than saving one directory level.
- **Honor the step-by-step escape hatch.** The default flow consolidates approvals (one sanity check + one unified proposal). If the user signals they want fine-grained review — phrases like "walk me through each step," "one piece at a time," "let me review each part" — revert to the old expanded flow: expose flow discussion as its own approval moment (step 5), structure proposal as its own (step 6), target path as a separate ask (old step 10). The work is identical; only the presentation changes.

---

## Exit criteria

You're done when:
- Target folder exists with the full structure: root holds `CLAUDE.md`, `README.md`, `.gitignore`; plus the dirs `.scaffolding/` (transient scaffolder state), `components/`, `data/`, `output/`, `PRPs/`, `.claude/`
- `.scaffolding/` contains `manifest.json` (authoritative lifecycle + component tracker), `README.md` (first-run onboarding), and optionally `start.bat`/`start.sh` (auto-chain helper, self-deleting on launch). The whole folder is auto-deleted by `/execute-prp` on successful v1 build.
- `PRPs/source/INITIAL.md` contains the pre-filled spec (ships in its final home — no relocation expected)
- Each `data/<source>/` and `output/<component>/` contains a one-line `README.md` (not `.gitkeep`)
- Any approved `project_level_folders` (e.g., `notebooks/`, `templates/`) exist at the project root with their own one-line `README.md` — or none if the user approved no extras
- Every component has a populated `components/<name>/` folder with its own README.md
- The project's `CLAUDE.md` has the project-structure enforcement block + one component section per component + aggregated validation
- `.scaffolding/README.md` exists with "Two stages / First time with Claude Code / What was set up / Build your project / Optional setup / Where to learn more / Cleanup" sections. The Optional setup section lists only items ce-scaffold returned (plus an optional git bullet — the scaffolder never runs `git init`). The Cleanup section notes that `/execute-prp` auto-deletes the folder.
- The user receives direct step-by-step handoff instructions (`cd <path> && claude` → type `/execute-prp PRPs/v1_<slug>.md`) plus explicit mention that `.scaffolding/` is auto-deleted on successful build.

---
description: Guided interview that researches, plans and scaffolds a new structured Claude Code project in the current folder
---

# /new-project

Guided conversational scaffolder using **parallel sub-agent orchestration**. A scaffolded project is a well-organized workspace containing **one or more components** — each component is a purposeful, named piece of work (an analysis, a CLI, a report, etc.) and maps to a single pattern from `${CLAUDE_PLUGIN_ROOT}/patterns/`.

**Two locations — never mix them up:**
- **Plugin files** (read-only templates): everything this command reads — `${CLAUDE_PLUGIN_ROOT}/patterns/`, `${CLAUDE_PLUGIN_ROOT}/deploy/`, `${CLAUDE_PLUGIN_ROOT}/agents/` — lives in the plugin's install folder, `${CLAUDE_PLUGIN_ROOT}`. Never write there.
- **The new project** (everything you write): the target path chosen in section 8, which defaults to the user's current working directory. Every relative path in this document (`components/`, `PRPs/`, `.claude/`, `.scaffolding/`, …) is relative to that target path.

Use this when the user:
- Runs `/new-project` explicitly
- Says anything like "I want to start a new project," "help me build something," "make me a [thing]"
- Is clearly non-technical and needs help figuring out what they even need

**Your role**: you're the **orchestrator** coordinating specialist sub-agents. You handle the conversation with the user; sub-agents handle research, design synthesis, per-component scaffolding, and validation in isolated context. Never dump technical jargon on the user. If you have to say something technical, briefly explain it in plain language.

---

## Core concept: projects contain components

A project is a named workspace with its own folder structure. Inside it live 1 or more **components** — each component solves one piece of the user's overall goal.

Example: a user says "I want to analyze our support tickets, generate a weekly report, and have a CLI to trigger a refresh." That's one project (`support_workflow`) with three components: `ticket_insights` (analysis), `weekly_report` (report), `refresh_cli` (cli).

Each component maps to one pattern in `${CLAUDE_PLUGIN_ROOT}/patterns/`. Components share the project's `data/` (inputs) and `output/` (artifacts) directories.

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

**Custom sub-agents** ship with this plugin in `${CLAUDE_PLUGIN_ROOT}/agents/` and are registered under the plugin's namespace:
- `project-scaffolder:ce-researcher` — web research + pattern extraction + gotcha mining (per component)
- `project-scaffolder:ce-planner` — synthesizes multi-component design proposal
- `project-scaffolder:ce-scaffold` — writes one component's folder (per component, parallel)
- `project-scaffolder:ce-validator` — post-scaffold smoke checks

Dispatch them via the **Task tool**, setting `subagent_type` to the namespaced agent name above (e.g. `project-scaffolder:ce-researcher`). If the Task tool rejects that name, check the available agent list for the `ce-*` entries and use the exact name it shows. They run in isolated context with their own tool access; the main session stays clean.

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

**Break the user's intent into 1-N components silently** (each purposeful, snake_case-named, mapped to one pattern from `${CLAUDE_PLUGIN_ROOT}/patterns/`). Then show a one-line sanity check:

> I'll set this up as **3 components**: `ticket_insights` (pattern analysis), `weekly_report` (recurring report), `refresh_cli` (CLI tool).
>
> Sound right, or want a different breakdown?

If the user replies "yes" / "looks good" / "go" / silence-after-beat → proceed to section 4 (classification is already done internally). If they want changes → iterate once, then proceed.

**Do NOT** show per-component descriptions, flow arrows, or folder trees here. Those all consolidate into section 8's unified proposal. This is just a component-count + naming check.

**Name suggestions — guidelines (apply silently when proposing):**
- snake_case, short, descriptive
- Nouns for things that produce artifacts (`weekly_report`, `customer_summary`)
- Verbs or verb+noun for tools that do things (`refresh_cli`, `send_digest`)

**Edge cases (handle in the one-line sanity check, not a separate conversation):**
- **User describes one thing**: still use `components/<name>/` for consistency. Say "1 component: `<name>`" — no defense needed.
- **User describes something huge**: push back before the sanity check. "This sounds like multiple projects — let me scope v1 to [X] and we can add more later. OK?" Only show the sanity check once the scope is reasonable.
- **Two "components" are really one thing**: merge silently. Don't surface the internal debate to the user.

**Escape hatch**: if the user signaled during the greeting or interview ("walk me through each step"), revert to the old-style expanded proposal with per-component descriptions, flow discussion as a separate step, structure approval as a separate step, etc. See Guidelines below.

---

### 4. Classify each component to a pattern

**Quietly** (don't announce the table) — for each component, pick one pattern file:

| Component purpose | Pattern file | Default stack |
|---|---|---|
| Interactive view of existing data | `${CLAUDE_PLUGIN_ROOT}/patterns/dashboard.md` | Python + Streamlit |
| Simple list/status of items | `${CLAUDE_PLUGIN_ROOT}/patterns/tracker.md` | Python + markdown files |
| Gather info, synthesize, deliver a written report | `${CLAUDE_PLUGIN_ROOT}/patterns/research.md` | Markdown-based research workflow, no code needed |
| Examine a dataset, produce findings | `${CLAUDE_PLUGIN_ROOT}/patterns/analysis.md` | Python + pandas |
| Recurring report combining data + narrative (weekly/monthly/exec summary) | `${CLAUDE_PLUGIN_ROOT}/patterns/report.md` | Python + pandas + Jinja2 |
| PRD, one-pager, launch brief, product doc | `${CLAUDE_PLUGIN_ROOT}/patterns/product_doc.md` | Markdown (+ optional pandoc for PDF) |
| Form input → stored → summary view | `${CLAUDE_PLUGIN_ROOT}/patterns/form_view.md` | Python + FastAPI + Jinja / Streamlit |
| Runs on a schedule, processes things, notifies | `${CLAUDE_PLUGIN_ROOT}/patterns/automation.md` | Python script + cron |
| CRUD API with auth | `${CLAUDE_PLUGIN_ROOT}/patterns/api.md` | Python + FastAPI + SQLAlchemy |
| Command-line tool | `${CLAUDE_PLUGIN_ROOT}/patterns/cli.md` | Python + click / Typer |
| System-to-system integration | `${CLAUDE_PLUGIN_ROOT}/patterns/integration.md` | Python + requests + SQLAlchemy |

Read each matching `${CLAUDE_PLUGIN_ROOT}/patterns/<shape>.md` to understand its default stack, folder conventions, and I/O expectations.

---

### 5. Work out flow and structure silently (no user approval yet)

**Don't announce this step** — it happens internally between the component sanity check and the research dispatch. The user sees no output here.

Do this work:

1. **Determine each component's inputs and outputs.** For each component, what data sources does it read from (`data/<source>/`) and where do its artifacts land (`output/<component>/<YYYY-MM-DD>_<run>/`)? Infer from the interview — if the user said "I want Monday reports from the ticket data," the flow is obvious. Ask only if a component's I/O is genuinely ambiguous after the interview (rare).
2. **Decide the folder structure.** Canonical: `components/`, `data/<source>/`, `output/<component>/`, `PRPs/`, `.claude/`, plus the `data/<source>/` subfolders for declared sources and `output/<component>/` subfolders for producing components. Write it down as a **project tree** (plain text, one line per folder with a short purpose). This tree is reused verbatim later: in the scaffolding manifest (section 9), the project `README.md` (item 7 of 9a) and the root `CLAUDE.md` structure block (9c). Add any approved `project_level_folders` to it after section 8.
3. **Decide each component's `secret_keys`.** For every external service a component talks to (an API, a database with a password, a webhook), name the environment variable(s) it will need in `UPPER_SNAKE_CASE` plus a one-line "where to get it" hint — e.g. `ZENDESK_API_TOKEN — Admin Center > Apps and integrations > APIs`. Key **names** only; never ask the user for a value. Components with no external credentials get an empty list. The union across components is the project's `secret_keys`; it feeds ce-scaffold (9b), `.env.example` (item 10 of 9a) and ce-validator (section 10).

**Conventions (apply silently):**
- Output: `output/<component_name>/<YYYY-MM-DD>_<run_description>/` — date first, never overwrite.
- Input: `data/<source_name>/` — one subfolder per external source, named by the source.
- Every component that produces artifacts has a dedicated output folder.

**The user will see all of this once, unified, in section 8** (design proposal). Don't surface it piecemeal here — that's the whole point of the consolidation.

**Escape hatch**: if the user asked for step-by-step mode earlier, revert to the old per-step surfacing — announce "Now let's map how data flows," show flow arrows, get approval; then announce structure proposal, show tree, get approval. See Guidelines.

---

### 6. Dispatch ce-researcher per component (parallel)

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

> Task tool, `subagent_type: "project-scaffolder:ce-researcher"`, one call per component:
>
> ```
> User intent: <1-3 sentence summary of this specific component>
> Shape classification: ${CLAUDE_PLUGIN_ROOT}/patterns/analysis.md
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

### 7. Dispatch ce-planner

**Announce**:

> **Step 4/6 — Putting the design together**

Dispatch ce-planner via Task tool once with the full multi-component spec:

> Task tool, `subagent_type: "project-scaffolder:ce-planner"`, prompt:
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
> Data flow: <the arrows from section 5>
>
> Produce a user-facing multi-component design proposal.
> ```

ce-planner returns a proposal in plain language. Show it to the user essentially verbatim.

---

### 8. Unified proposal + iteration (the single big approval moment)

**Pre-compute the target path** before showing the proposal. Default: the user's **current working directory** (the folder Claude Code was started in) when it is empty — ignore a lone `.git/`. If it already holds other files, default to `<current working directory>/<slugified-project-name>` so nothing existing is touched. Use the absolute path. Never target anything inside `${CLAUDE_PLUGIN_ROOT}` — that is the plugin's install folder. No separate ask — the path is part of the proposal and the user can change it during iteration.

**Overwrite guard.** Never write into a folder that already has content. If the chosen target (the default `<cwd>/<slug>`, or a path the user names) already exists and contains anything besides a lone `.git/`, do **not** propose it silently: say so in the target-path line ("`<path>` already exists and has files in it — I won't write over them. Pick a different name/location, or tell me explicitly to use it anyway and I'll only add files that don't exist yet.") and wait for the answer. Check with the Glob or LS-style listing, not by assumption. Re-check right before 9a writes the first file — if the folder gained content since the proposal, stop and ask again. Even with permission to use a non-empty folder, never overwrite an existing file: skip it and list the skipped paths in the handoff.

**Show ce-planner's proposal verbatim, preceded by a target-path line.** The user sees one block with: target path + description + components + flow + stack + any extra top-level folders. Example shape:

> I'd create **`support_workflow`** right here, in `<current working directory>`. (Want a different location? Tell me during review.)
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

### 9. Scaffold

**Announce**:

> **Step 5/6 — Creating your project**
>
> Here's what I'm about to do:

Print a scaffolding manifest BEFORE files appear:

> ```
> Creating folder:           <target path>
>   ├─ .scaffolding/           (transient scaffolder state + first-run notes — auto-deleted by /execute-prp on successful build)
>   │    └─ README.md         (what's done + what's next + newcomer tips)
>   ├─ CLAUDE.md              (rules for Claude — your project structure + a component index)
>   ├─ README.md              (one-page overview)
>   ├─ pyproject.toml         (one dependency list + test config for the whole project)
>   ├─ PRPs/                  (implementation plans)
>   │    ├─ v1_<slug>.md       (the v1 build plan — /execute-prp follows it)
>   │    └─ source/
>   │         └─ INITIAL.md   (blank intake template for post-build features)
>   ├─ .claude/
>   │    ├─ settings.json          (shared, committed — deny rules and the guard hook that keep Claude away from your secrets)
>   │    ├─ settings.local.json    (yours only, git-ignored — pre-approves common build and test commands)
>   │    ├─ hooks/                (guardrail that stops tool calls reaching for your .env)
>   │    └─ commands/              (/new-feature, /generate-prp, /execute-prp, /handoff, /deploy-status)
>   ├─ components/
>   │    ├─ <component_1>/      (+ its own CLAUDE.md — rules load only when Claude works here)
>   │    ├─ <component_2>/
>   │    └─ <component_3>/
>   ├─ data/
>   │    └─ <source>/           (for your inputs)
>   ├─ output/
>   │    ├─ <component_1>/      (for its artifacts)
>   │    └─ <component_2>/
>   ├─ tests/                  (project-wide tests, incl. a structural hygiene check)
>   └─ .gitignore             (ready if you choose to `git init` later — optional)
> ```
>
> *(If any component declared secrets, add these two lines before the `tests/` line — omit both when the project needs no secrets:)*
>
> ```
>   ├─ .env.example           (the secret keys this project needs — names only, safe to commit)
>   ├─ scripts/
>   │    └─ secure/            (Set-ProjectSecrets.ps1 writes your .env; Test-Readiness.ps1 checks it)
> ```
>
> *(If the user approved any `project_level_folders` during design iteration, add one line per folder before the `.gitignore` line — e.g., `>   ├─ notebooks/             (exploratory hypothesis-testing outside the analysis pipeline)`. Omit entirely if the list is empty.)*
>
> Writing files now...

#### 9a. Main session writes the project-root skeleton

All sourced from **`${CLAUDE_PLUGIN_ROOT}/deploy/`** unless noted. Treat `${CLAUDE_PLUGIN_ROOT}/deploy/` as the canonical template; plugin files outside `deploy/` are never copied. Copy with the Read and Write tools (or `cp` with both paths quoted — the plugin folder can contain spaces); the destination is always inside the target path.

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
   - `PRPs/source/` — holds `INITIAL.md` (written in item 6 below), so no `.gitkeep` is needed
   - `tests/` — project-wide tests; receives `test_repo_hygiene.py` in item 9

2. **`.claude/settings.json`** — copy from `${CLAUDE_PLUGIN_ROOT}/deploy/.claude/settings.json`. It is the **shared, committed** project settings file (permissions + the secret-guard hook), so the protection travels with the repo to every teammate. It holds the deny rules and the hook only.

   **`.claude/settings.local.json`** — copy from `${CLAUDE_PLUGIN_ROOT}/deploy/.claude/settings.local.json`. It pre-approves common build, test and read-only commands (`python`, `pytest`, `npm`, `ls`, ...) for the person who ran the scaffolder. It is personal and git-ignored, so cloning the repo never pre-approves commands for someone else. Never move the deny rules or the hook into it.

   **`.claude/hooks/`** — copy both `${CLAUDE_PLUGIN_ROOT}/deploy/.claude/hooks/block_secret_access.py` and `${CLAUDE_PLUGIN_ROOT}/deploy/.claude/hooks/run_python_hook.sh` unchanged. `settings.json` runs the Python guard through the `.sh` launcher in a `PreToolUse` hook; the launcher finds a working Python 3 (`python3`, `python`, or `py -3`) and **fails closed** — if the files are missing or no interpreter works, every guarded tool call is blocked with an explanation rather than silently allowed. Copy them for every project, secrets or not — the guard is inert when no `.env` exists.

3. **`.claude/commands/`** — copy all five from `${CLAUDE_PLUGIN_ROOT}/deploy/.claude/commands/`: `new-feature.md`, `generate-prp.md`, `execute-prp.md`, `handoff.md`, `deploy-status.md`.

4. **`.gitignore`** — copy from `${CLAUDE_PLUGIN_ROOT}/deploy/.gitignore`.

5. **`PRPs/templates/prp_base.md`** + **`PRPs/README.md`** — copy both from `${CLAUDE_PLUGIN_ROOT}/deploy/PRPs/`.

6. **`PRPs/source/INITIAL.md`** — copy `${CLAUDE_PLUGIN_ROOT}/deploy/INITIAL.md` as-is (blank template). In the option-B flow, `INITIAL.md` is the **per-feature intake for post-build feature work**, not the scaffold spec — so it ships empty, waiting for the user's next feature idea. The v1 implementation plan is written directly to `PRPs/v1_<project_slug>.md` in section 9d below, not funneled through INITIAL.md.

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
   - "Project structure" — the project tree from section 5 (the same tree the scaffolding manifest in section 9 showed the user)
   - "Components" — one line per component: name → purpose → pattern
   - "How to run" — the entry command per component (e.g., `streamlit run components/<name>/app.py`, `python components/<name>/scripts/run.py`), preceded by one line: "Run these with the project venv active, or call its interpreter directly — `.venv\Scripts\python ...` on Windows, `.venv/bin/python ...` on macOS/Linux (bare `python` usually doesn't exist on macOS)."
   - "How to develop with Claude" — brief pointer for the initial build (`/execute-prp PRPs/v1_<slug>.md`) AND for adding features after build (`/new-feature` for the guided path, or manually edit `PRPs/source/INITIAL.md` → `/generate-prp` → `/execute-prp PRPs/<slug>.md`)
   - "How to reopen this project in Claude Code" — one line: `cd "<project path>"`, then `claude` (two commands — `&&` fails in Windows PowerShell 5.1) (no launcher scripts ship)
   - One line at the top directing newcomers to `.scaffolding/README.md` for first-time setup (mention it will be auto-deleted by `/execute-prp` on successful build)

8. **Project-level folders approved during design iteration.** For each entry in `project_level_folders` (may be empty):
   - Create `<project_root>/<folder_name>/`
   - Write `<project_root>/<folder_name>/README.md` with shape:
     ```
     # <folder_name>

     <purpose line from the approved suggestion>
     ```
   Same one-line-README convention as `data/<source>/README.md` and `output/<component>/README.md`. If the user added a folder during iteration without providing a purpose, use `Added by user — edit this README to describe what goes here.` as the purpose line.

9. **Root `pyproject.toml` + `tests/test_repo_hygiene.py`** (Python stacks — the default for every current pattern; skip both for a non-Python stack).

   Write these **after** the ce-scaffold reports return in 9b, since the dependency list is aggregated from them.

   Write it from this template — **every section is required**, fill only the `<...>` placeholders:

   ```toml
   [build-system]
   requires = ["setuptools>=64"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "<project_slug, lowercased; letters, digits, - and _ only>"
   version = "0.1.0"
   requires-python = ">=3.11"
   dependencies = [
       # deduplicated union of every component's `## Dependencies` return
   ]

   [project.optional-dependencies]
   dev = ["pytest>=8", "ruff>=0.5", "mypy>=1.10"]

   # Components are run as scripts/apps from components/<name>/, not installed as
   # packages. Without this line, setuptools auto-discovery sees components/, data/,
   # output/ ... and `pip install -e .` fails with "Multiple top-level packages".
   [tool.setuptools]
   packages = []

   [tool.pytest.ini_options]
   testpaths = ["tests", "components"]
   # importlib mode: every component has tests/__init__.py + test_*.py with the same
   # names; the default (prepend) mode then fails with "import file mismatch".
   addopts = "-q --tb=short --no-header -ra --maxfail=3 --import-mode=importlib"
   # importlib mode doesn't touch sys.path, so tests import component code as
   # `components.<name>.<module>` from the project root.
   pythonpath = ["."]
   cache_dir = "~/.cache/pytest"

   [tool.ruff]
   output-format = "concise"
   cache-dir = "~/.cache/ruff"

   [tool.mypy]
   cache_dir = "~/.cache/mypy"
   # Same collision as pytest's: every component has a `tests` package. With this,
   # mypy names modules by path (components.<name>.tests) instead of failing with
   # 'Duplicate module named "tests"'.
   explicit_package_bases = true
   ```

   `[project] dependencies` is the deduplicated union of every component's `## Dependencies` return. Where two components pin conflicting ranges, take the intersection and note it in the handoff. Test/lint tools go in the `dev` extra, not in `dependencies`.

   **Exception — a `cli` component that installs a console script** (`${CLAUDE_PLUGIN_ROOT}/patterns/cli.md`): replace the `[tool.setuptools] packages = []` table with that pattern's `[tool.setuptools.packages.find] where = ["components/<component_name>/src"]` and add its `[project.scripts]` entry. Never keep both tables. Only one component per project can own package discovery this way; flag a second one in the handoff.

   The tool config is **not optional boilerplate — copy it verbatim.** These flags exist to keep validation-gate output small, because `/execute-prp` runs those gates repeatedly against failing code and every extra line lands in the context window. Measured on a 4-test file with 3 failures: the pytest flags cut output 39%, and `output-format = "concise"` cuts ruff 61% (ruff's default reprints the source snippet under every violation). Nothing actionable is lost — `concise` keeps `path:line:col: CODE message` and the `[*]` auto-fixable marker.

   `--maxfail=3` caps the blast radius of a broken change without hiding whether one thing or everything broke. Cache dirs point outside the tree per `${CLAUDE_PLUGIN_ROOT}/deploy/CLAUDE.md`'s "Tool caches outside the project" rule. Add `[tool.ruff] select`/`target-version` to match the project stack.

   Copy `${CLAUDE_PLUGIN_ROOT}/deploy/tests/test_repo_hygiene.py` to `tests/test_repo_hygiene.py` unchanged. It enforces the 500-line rule and the no-artifacts-at-root rule that `CLAUDE.md` declares.

   **One environment, one install.** The project's first-run setup is exactly two lines. Emit the pair matching the user's platform (from your environment info — `win32`, `darwin`, `linux`), not both:
   ```
   # Windows (PowerShell or cmd)
   python -m venv .venv
   .venv\Scripts\python -m pip install -e ".[dev]"

   # macOS / Linux — use python3: macOS has no `python` command by default
   python3 -m venv .venv
   .venv/bin/python -m pip install -e ".[dev]"
   ```
   On Windows, if `python` opens the Microsoft Store or says "Python was not found", use `py -m venv .venv` instead. Calling the venv's own interpreter (`.venv\Scripts\python` / `.venv/bin/python`) avoids needing to activate the venv and avoids PowerShell's activation-script execution policy. Never emit per-component install lines — components share one interpreter.

10. **Secrets scaffolding** — only when the project's `secret_keys` (section 5, unioned with every component's `## Secret keys` return) is **non-empty**. When it's empty, skip this item entirely: no `.env.example`, no `scripts/`. (The deny rules and the guard hook in `.claude/settings.json` ship either way.)

    - **`.env.example`** at the project root, built from that union. One comment line per key carrying the "where to get it" hint, then the bare key. Never any value:
      ```
      # Zendesk API token — Admin Center > Apps and integrations > APIs
      ZENDESK_API_TOKEN=
      ```
      If two components declare the same key, it appears once.
    - **`scripts/secure/`** — copy both files from `${CLAUDE_PLUGIN_ROOT}/deploy/scripts/secure/` (`Set-ProjectSecrets.ps1`, `Test-Readiness.ps1`) unchanged.

**Do NOT run `git init`.** The user might not want version control in this folder, or might plan to place it inside an existing repo. `.scaffolding/README.md` surfaces `git init` as one optional setup item — the user decides.

#### 9b. Dispatch ce-scaffold per component (parallel)

For each component, dispatch ce-scaffold via Task tool — all in a single message so they run in parallel:

> Task tool, `subagent_type: "project-scaffolder:ce-scaffold"`, one call per component:
>
> ```
> project_root: <absolute target path>
> component_name: <snake_case name>
> pattern_file: ${CLAUDE_PLUGIN_ROOT}/patterns/<shape>.md
> purpose: <one-paragraph description>
> inputs: <declared input path(s) or "none">
> outputs: <declared output path>
> project_stack: <primary language — e.g., "Python 3.11">
> secret_keys: <this component's keys from section 5, one per line as "KEY_NAME — where to get it", or "none">
> ```

Each ce-scaffold instance writes `components/<name>/` in isolation — including that component's own `CLAUDE.md` carrying the pattern gotchas — and returns:
- Files it created
- Validation commands for this component (aggregated into the root CLAUDE.md's validation gates)
- **Dependencies** — the libs from the pattern's default stack (aggregated into the root `pyproject.toml`, item 9 of 9a)
- **Secret keys** — key NAMES only: the `secret_keys` you passed in, plus any the pattern itself requires (aggregated into the root `.env.example`, item 10 of 9a). If a report adds a key you didn't pass, add it to the project's `secret_keys` too.
- **First-run setup commands** — component-specific one-offs only, usually empty; aggregated into `.scaffolding/README.md`'s Optional setup list
- Any flags for dependency conflicts

Gotchas are **not** returned — ce-scaffold writes them straight into `components/<name>/CLAUDE.md`, where Claude Code loads them on demand.

#### 9c. Build project CLAUDE.md, the .scaffolding/ manifest + README, dynamically

**First, complete the two deferred items from 9a** now that the reports are in: item 9 (root `pyproject.toml` from the aggregated `## Dependencies`, plus `tests/test_repo_hygiene.py`) and item 10 (root `.env.example` from the project's `secret_keys` unioned with the aggregated `## Secret keys`, plus `scripts/secure/` — skipped entirely when that union is empty).

Then **you** (main session) write the project's `CLAUDE.md` by assembling:

```markdown
# Project: <Project Name>

<one-paragraph plain-language description>

**Stack**: <languages/frameworks used across components>

---

## Project structure (STRICT — do not deviate)

```
<the project tree from section 5, verbatim>
```

**Enforcement rules:**
- Components live in `components/<name>/` only — never loose at project root
- All inputs live in `data/<source>/` — never inside a component folder
- All outputs land in `output/<component>/<YYYY-MM-DD>_<description>/` — never at project root, never overwriting prior runs
- Never add a new top-level folder without updating this section first
- Never rename `components/`, `data/`, `output/`, or `PRPs/`
- All secrets live in the project-root `.env` — never a component-local `.env`, never in code or config
- All dependencies live in the project-root manifest — never a component-local `requirements.txt`
{If `project_level_folders` is non-empty, inject an extra bullet here listing each one by name with its purpose — e.g., `- Project-level folders \`notebooks/\` (exploratory hypothesis-testing) and \`templates/\` (shared report layouts) are part of this project's declared structure — use each as described in its README; don't improvise alternatives.` Omit this bullet entirely if no extras were approved.}

---

## Components

| Component | Pattern | Purpose | How to run |
|---|---|---|---|
| `<component_1>` | `<pattern_name>` | <one line, lowercase> | `<the one command>` |
| `<component_2>` | `<pattern_name>` | <one line, lowercase> | `<the one command>` |
| `<component_3>` | `<pattern_name>` | <one line, lowercase> | `<the one command>` |

Per-component gotchas and I/O paths live in `components/<name>/CLAUDE.md`. Read that file before editing a component — it loads automatically once you open a file in that folder, but not while you're only planning.

---

## Validation gates

```bash
<aggregated validation commands from every component's ce-scaffold return>
```

---

<then append ${CLAUDE_PLUGIN_ROOT}/deploy/CLAUDE.md verbatim — the generic Session Start / Context Discipline / Code / Testing / Docs / AI Behavior / Project Cleanliness / Task Completion sections>
```

**Why this structure:** the project-specific enforcement rules and per-component gotchas sit at the TOP. Claude reads these first and knows the structural contract before falling through to generic defaults.

**Then write `.scaffolding/manifest.json`**. The `.scaffolding/` folder is the sole location for all transient scaffolder state — it will be auto-deleted by `/execute-prp` on successful v1 build, leaving no scaffolder footprint in the finished project. The manifest is the authoritative status source during the plan → built transition. Shape:

```json
{
  "scaffold_version": 2,
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
- `scaffold_version` is **2**. Version 1 projects have a different layout: per-component gotchas inside the root `CLAUDE.md`, component-local `requirements.txt` and `.env.example`, no `components/<name>/CLAUDE.md`, no root `pyproject.toml`, and an empty `permissions.deny`. Those projects still work — they carry their own copy of the slash commands from the day they were scaffolded — but don't assume a v1 project has the v2 layout when inspecting one.
- `lifecycle.stage` is `"plan"` at `/new-project` time — the PRP is written at scaffold time (section 9d), so the project goes straight to plan stage. `/execute-prp` advances it to `"built"` on first successful full build AND flips every component's `scaffold_state` from `"stub"` to `"built"` at the same time. Each stage transition appends a `{stage, at, by}` entry to `lifecycle.history`. Two stages total — `"scaffold"` is not an observable state in the option-B flow.
- `scaffold_state` at the component level is `"stub"` at scaffold time and only flips to `"built"` inside `/execute-prp` when that component's section of the PRP passes validation. It exists separately from `lifecycle.stage` so `/execute-prp --component <name>` (partial builds) can reflect per-component build state while the project-level stage stays at `"plan"` until ALL components are built.
- `entry_command` comes from the component's row in the root `CLAUDE.md`'s Components table ("How to run" column).
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
- `CLAUDE.md` — project rules + a component index (auto-loaded every Claude Code session). Each component's own gotchas live in `components/<name>/CLAUDE.md` and load only when Claude works in that folder, so the root file stays small as the project grows.
- `README.md` — one-page overview
- `pyproject.toml` — every component's dependencies in one place, plus test config. One environment, one install.
- `tests/` — project-wide tests, including a structural check that keeps source files under 500 lines
- `.claude/` — shared settings (`settings.json`: permissions, including deny rules and a guard hook that keep Claude from reading your `.env`) and the five slash commands: `/new-feature`, `/generate-prp`, `/execute-prp`, `/handoff`, `/deploy-status`
<include the next two bullets only when the project declares secrets:>
- `.env.example` — the secret keys this project needs, names only. Safe to commit.
- `scripts/secure/` — `Set-ProjectSecrets.ps1` writes your `.env`; `Test-Readiness.ps1` reports which keys are set without revealing any value
- `.gitignore` — ready if you want to use git (no repo initialized — see optional setup below)

## Build your project (inside Claude Code)

1. Open a terminal and run: `cd "<project path>"`, then `claude` (two commands — `&&` fails in Windows PowerShell 5.1)
2. *(Optional)* Skim `PRPs/v1_<slug>.md` to see what Claude plans to build
3. Type `/execute-prp PRPs/v1_<slug>.md` — Claude builds the components and runs validation gates

That's it — one command to go from scaffold to working v1.

## Optional setup

`/execute-prp` handles the build. These are the things it can't do for you.

- [ ] Create the environment and install everything (including test/lint tools), once:
      ```
      python -m venv .venv
      .venv\Scripts\python -m pip install -e ".[dev]"
      ```
      <on macOS/Linux emit instead: `python3 -m venv .venv` then `.venv/bin/python -m pip install -e ".[dev]"`. On Windows add: "If `python` isn't found, use `py -m venv .venv`.">
<include the next bullet only when the project has a .env.example:>
- [ ] Fill in your secrets **in your own terminal, not through Claude**: <Windows:> `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\secure\Set-ProjectSecrets.ps1` <macOS/Linux:> `pwsh -File scripts/secure/Set-ProjectSecrets.ps1` if PowerShell 7 is installed, otherwise `cp .env.example .env` and edit it by hand. The script prompts for each key in `.env.example` and writes `.env`; values stay hidden as you type and are never echoed back. Claude is kept away from `.env` by the deny rules and guard hook in `.claude/settings.json` — it can run `Test-Readiness.ps1` (same invocation) to see which keys are set, by name only.
<then the aggregated first_run_setup lines from ce-scaffold reports, deduplicated, one bullet each — usually none. e.g.:>
- [ ] `playwright install chromium`
- [ ] Want version control? `git init && git add . && git commit -m "Initial scaffold"`
<the install bullet always appears for a Python stack; the git bullet always appears unless the user explicitly said they don't use git during the interview>

## Where to learn more

- `../CLAUDE.md` — rules Claude follows across the whole project
- `../PRPs/README.md` — how the PRP workflow works end to end
- `../components/<name>/README.md` — per-component orientation (for you)
- `../components/<name>/CLAUDE.md` — per-component rules (for Claude; loads only when it works in that folder)

## Cleanup

Automatic — on a successful `/execute-prp PRPs/v1_<slug>.md` run, this whole folder is deleted along with the status banner in `../README.md`. No action needed.
```

**Assembly rules for `.scaffolding/README.md`:**

- Target length: ~45-55 lines. If it's longer, compress.
- "The two stages" block stays first — this is the main orientation most new users need.
- "What was set up" is mostly static — only the component-count hint and the v1 PRP slug vary. Never claim a git repo exists (the scaffolder doesn't create one).
- "Optional setup" order is fixed: the venv/install block first, then the secrets bullet (only when `.env.example` exists), then any `first_run_setup` lines ce-scaffold returned, then the git bullet last so users who don't use git can ignore the tail cleanly.
- Do NOT include stack conjecture — beyond the install and secrets bullets, only emit setup items ce-scaffold explicitly returned.
- The secrets bullet must say **in your own terminal, not through Claude** — Claude Code runs shell commands with stdin at the null device, so the prompt loop would silently write empty values.
- Framing matters: "optional" not "required." A user should feel comfortable skipping git entirely.
- Keep the "Cleanup" section — it's the explicit signal that the folder is safe to delete.
- The PowerShell invocations use `-ExecutionPolicy Bypass -File` on purpose: running `.\scripts\secure\X.ps1` directly fails on a default Windows client ("running scripts is disabled on this system"), and `powershell` (Windows PowerShell 5.1) ships with every Windows, while `pwsh` (PowerShell 7) often isn't installed. Both scripts work under either.
- Paths in the "Where to learn more" section are written relative to `.scaffolding/` (so prefix them with `../`).

After both files are written, print:

> All files created.

#### 9d. Write the v1 mega-PRP inline

**You** (main session) now synthesize `PRPs/v1_<project_slug>.md` directly — no intermediate INITIAL.md, no `/generate-prp` step. You already have every piece of context needed: the user interview, ce-researcher briefs per component, ce-scaffold returns (stub files + validation commands + dependencies + secret keys), the per-component gotchas ce-scaffold wrote into `components/<name>/CLAUDE.md`, the design proposal, data flow, build order rationale, and (if present) the user's pre-written `REQUIREMENTS.md`.

Follow the shape of `PRPs/templates/prp_base.md` (the copy you wrote into the project in 9a) adapted for multi-component scope. Target ≤ 800 lines — if heading longer, you're duplicating CLAUDE.md content; cite instead of inline.

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

### 10. Dispatch ce-validator

**Announce** (fold under the user-facing Step 5 — verification is the tail end of "create", not a separate user-facing step):

> Verifying everything looks good...

Dispatch ce-validator via Task tool:

> Task tool, `subagent_type: "project-scaffolder:ce-validator"`, prompt:
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
> secret_keys: <the project's secret_keys union — key NAMES only, or empty list>
>
> Run validation and return a report.
> ```

Based on result:
- **PASS** → proceed to handoff
- **WARN** → minor issue. Either quickly patch before handoff OR mention to user ("I noticed X; it's minor, fix it in your first session")
- **FAIL** → blocker. Address, re-run validator.

---

### 11. Handoff — offer auto-chain or hand off cleanly

**Announce**:

> **Step 6/6 — Ready to go!**

**Ask the auto-chain question** first (don't dump OS-specific instructions yet):

> Your project is ready at `<target path>`. The implementation plan is already written at `PRPs/v1_<slug>.md`.
>
> **Ready to build?** I can launch your new project and kick off `/execute-prp PRPs/v1_<slug>.md` automatically — Claude will fill in the stubs with real code and run validation gates. Or say "not yet" if you want to review the scaffold + PRP first.
>
> **[yes / not yet]**

**If the user says yes** (auto-chain path):

1. Take the OS from your environment info (`Platform: win32` / `darwin` / `linux`) — don't shell out to `uname`, which doesn't exist in cmd or PowerShell.
2. Write a one-time helper script inside `.scaffolding/` (the folder you already created in 9c). The script cd's to the parent (project root) before launching Claude Code, and deletes only itself on exit — the `.scaffolding/README.md` stays so the user can read it during their first session:
   - **macOS / Linux** — `<target>/.scaffolding/start.sh`:
     ```bash
     #!/usr/bin/env bash
     # One-time auto-chain helper — deletes itself, then launches Claude Code.
     self="${BASH_SOURCE[0]}"
     cd "$(dirname "$self")/.."
     rm -- "$self"
     exec claude "/execute-prp PRPs/v1_<slug>.md"
     ```
     `chmod +x` it. Substitute the actual slug. Write it exactly as shown: it deletes itself before `exec` because `exec` replaces the shell, so an `EXIT` trap would never run.
   - **Windows** — `<target>\.scaffolding\start.bat`:
     ```batch
     @echo off
     cd /d "%~dp0..\"
     claude "/execute-prp PRPs/v1_<slug>.md"
     del "%~f0"
     ```
     Substitute the actual slug.
3. Launch it in a new window from the orchestrator session:
   - **macOS**: `open -a Terminal "<target>/.scaffolding/start.sh"`
   - **Linux**: `(x-terminal-emulator -e "<target>/.scaffolding/start.sh" &) 2>/dev/null || (gnome-terminal -- "<target>/.scaffolding/start.sh" &) 2>/dev/null || true`
   - **Windows, from the Bash tool (Git Bash)**: `MSYS_NO_PATHCONV=1 cmd /c start "" "<target>\.scaffolding\start.bat"` — use the backslashed Windows path. `MSYS_NO_PATHCONV=1` is required: without it Git Bash rewrites `/c` (and any other `/x` argument) into a filesystem path and the window never opens. Do **not** use a bare `start ""` either — in Git Bash that's a shell script wrapper, not cmd's builtin.
   - **Windows, from the PowerShell tool**: `Start-Process -FilePath "<target>\.scaffolding\start.bat"`
   If the launch command errors, skip straight to the manual fallback below — don't retry variants.
4. Print confirmation with direct, step-by-step manual fallback:

   > Launching... a new terminal window should open with `/execute-prp PRPs/v1_<slug>.md` already running in your new project.
   >
   > **If the new window doesn't appear within ~5 seconds**, do this instead:
   >
   > 1. Open a terminal and run: `cd "<target path>"`, then `claude` (two commands — `&&` fails in Windows PowerShell 5.1)
   > 2. When Claude Code opens, type `/execute-prp PRPs/v1_<slug>.md` and press Enter.
   >
   > **Heads-up:** I created a hidden folder called `.scaffolding/` inside your project. It contains the scaffold manifest, first-run notes, and optional setup steps (install deps, copy `.env`, `git init`). **`/execute-prp` will delete this folder automatically when the v1 build succeeds** — leaving your project clean and ready for real work. Read `.scaffolding/README.md` if you want the extra context first.

**If the user says "not yet"** (manual path):

Show direct, step-by-step instructions — not "open this file and read it":

> Your project is ready at `<target path>`. When you're ready to build, do these two things:
>
> 1. **Open Claude Code in the project folder.** Open a terminal and run: `cd "<target path>"`, then `claude` (two commands — `&&` fails in Windows PowerShell 5.1)
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

If a developer explicitly asks for a *reusable context-engineering template* for a framework (not a project that uses it), that's outside `/new-project`'s scope. Tell them this plugin doesn't include a template generator, and exit. If they just want to build something that uses a specific framework, stay in `/new-project` and research the framework during the normal research step.

---

## Research/analysis route

If the user wants **pure knowledge work** — one or more research components, no code — you still use the component model:

- Component pattern is `${CLAUDE_PLUGIN_ROOT}/patterns/research.md` or `${CLAUDE_PLUGIN_ROOT}/patterns/product_doc.md`
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
- **Honor the step-by-step escape hatch.** The default flow consolidates approvals (one sanity check + one unified proposal). If the user signals they want fine-grained review — phrases like "walk me through each step," "one piece at a time," "let me review each part" — revert to the old expanded flow: expose the flow discussion (section 5, item 1) as its own approval moment, show the project tree (section 5, item 2) for its own approval, and ask for the target path separately before the section 8 proposal. The work is identical; only the presentation changes.

---

## Exit criteria

These restate the sections above; if one ever disagrees with a section, the section wins — fix the criterion.

You're done when:
- Target folder exists with the full structure: root holds `CLAUDE.md`, `README.md`, `.gitignore`; plus the dirs `.scaffolding/` (transient scaffolder state), `components/`, `data/`, `output/`, `PRPs/`, `.claude/`, `tests/` (Python stacks). No pre-existing file was overwritten (section 8 overwrite guard).
- `.scaffolding/` contains `manifest.json` (authoritative lifecycle + component tracker, `lifecycle.stage == "plan"`), `README.md` (first-run onboarding), and optionally `start.bat`/`start.sh` (auto-chain helper, self-deleting on launch). The whole folder is auto-deleted by `/execute-prp` on successful v1 build.
- `PRPs/v1_<slug>.md` exists (section 9d) — the v1 build plan.
- `PRPs/source/INITIAL.md` is the **blank** per-feature template copied from `deploy/INITIAL.md` (item 6 of 9a) — not pre-filled; `PRPs/templates/prp_base.md`, `PRPs/README.md` and `PRPs/archive/` exist.
- Each `data/<source>/` and `output/<component>/` contains a one-line `README.md` (not `.gitkeep`)
- Any approved `project_level_folders` (e.g., `notebooks/`, `templates/`) exist at the project root with their own one-line `README.md` — or none if the user approved no extras
- Every component has a populated `components/<name>/` folder with its own `README.md` **and its own `CLAUDE.md`** carrying that pattern's gotchas
- No component folder contains a `requirements.txt`, `pyproject.toml`, `package.json`, or `.env.example` — those are project-root concerns
- The root `pyproject.toml` exists (Python stacks) from the item 9 template: `[project]` name/version, the union of component dependencies, the `dev` extra, `[tool.setuptools] packages = []` (or the cli pattern's `packages.find`), and pytest `testpaths` + `--import-mode=importlib`; `tests/test_repo_hygiene.py` is present
- `.claude/settings.json` (not `settings.local.json`) has a non-empty `permissions.deny` covering `.env` / `.env.*` reads with `.env.example`/`.sample`/`.template` carved out, and a `PreToolUse` hook running `.claude/hooks/run_python_hook.sh` → `block_secret_access.py`; both hook files exist; all five slash commands are in `.claude/commands/`
- If the project's `secret_keys` is non-empty: `.env.example` exists at the project root with exactly those key names (no values), and `scripts/secure/` holds both PowerShell scripts. If it's empty, neither exists.
- The project's root `CLAUDE.md` has the project-structure enforcement block + a Components index table (one row per component, no gotcha bullets) + aggregated validation, and stays under 200 lines
- `.scaffolding/README.md` exists with "Two stages / First time with Claude Code / What was set up / Build your project / Optional setup / Where to learn more / Cleanup" sections. Optional setup holds, in order: the install block (Python stacks), the secrets bullet (only with `.env.example`), any `first_run_setup` lines ce-scaffold returned, and the git bullet — the scaffolder never runs `git init`. The Cleanup section notes that `/execute-prp` auto-deletes the folder.
- The user receives direct step-by-step handoff instructions (`cd "<path>"`, then `claude`, then type `/execute-prp PRPs/v1_<slug>.md`) plus explicit mention that `.scaffolding/` is auto-deleted on successful build.

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
> &nbsp;&nbsp;**Step 2** → We break the project into components (named pieces of work) and map out how data flows between them
> &nbsp;&nbsp;**Step 3** → I research the best way to build each component (takes ~30 seconds; I'll work quietly)
> &nbsp;&nbsp;**Step 4** → I propose a full project design in plain language for your approval
> &nbsp;&nbsp;**Step 5** → Once you approve, I create the project folder with all the components
> &nbsp;&nbsp;**Step 6** → I verify everything is in order
> &nbsp;&nbsp;**Step 7** → You open your new project with one click and we continue from there
>
> Usually takes 4-7 minutes. You'll see me work — I'll narrate what I'm doing.
>
> **Ready? Tell me — what are you trying to build?** A rough sentence is fine.

Then wait for the user's answer.

---

### 2. Interview — adaptive, conversational

**Announce the step**:

> **Step 1/7 — Understanding your goal**

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

### 3. Decompose into components

**Announce**:

> **Step 2/7 — Mapping the components**
>
> I'm going to break what you described into a few named pieces of work. Each piece does one thing cleanly. Tell me if the breakdown makes sense, or if you'd split it differently.

**Break the user's intent into 1-N components.** Each component is:
- **Purposeful** — does one thing
- **Named** — snake_case, descriptive (e.g., `ticket_insights`, `weekly_report`, `refresh_cli`)
- **Mapped to one pattern** from `patterns/` (see table in Step 4)

**Propose the breakdown in plain language, then confirm with the user:**

> Based on what you've described, I see three pieces:
>
> 1. **`ticket_insights`** — pulls patterns out of the raw support tickets (which tickets repeat, how long they take to resolve, what's trending). *This is a data analysis.*
> 2. **`weekly_report`** — takes the insights and turns them into a Monday-morning summary with a chart or two. *This is a recurring report.*
> 3. **`refresh_cli`** — one command you run when you want to re-pull the latest tickets into the project. *This is a CLI tool.*
>
> Does that match what you had in mind? Want to add, remove, or rename any of them?

**Name suggestions — guidelines:**
- snake_case, short, descriptive
- Use nouns for things that produce artifacts (`weekly_report`, `customer_summary`)
- Use verbs or verb+noun for tools that do things (`refresh_cli`, `send_digest`)
- Ask the user to confirm or rename — they know their domain vocabulary better than you do

**Edge cases:**
- **User describes one thing**: still use `components/<name>/` for consistency. One-component projects still benefit from the structure (clean separation between project infra and the thing itself).
- **User describes something huge**: push back gently. "This sounds like a multi-project effort — let's scope v1 down to [X]. We can add more later." Don't scaffold 8 components.
- **Two "components" are really one thing**: merge them. "The analysis and the report feel tightly coupled — want me to treat that as one `weekly_summary` component with both in it, or keep them separate so you can run the analysis without regenerating the report?"

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

### 5. Flow discussion — inputs and outputs per component

**Announce**:

> Now let's map how data flows through the components.

Walk through each component:

- **What are this component's inputs?** (data source, another component's output, none)
- **What are its outputs?** (files, a document, an API response, updates to a shared store)
- **Who/what triggers it?** (user runs it, a schedule, another component)

**Propose a data-flow summary in plain language:**

> Here's how the pieces connect:
>
> - `refresh_cli` pulls fresh tickets from Zendesk → saves them in `data/zendesk_exports/`
> - `ticket_insights` reads from `data/zendesk_exports/` → writes analysis to `output/ticket_insights/<date>_<run>/`
> - `weekly_report` reads the latest `output/ticket_insights/` → writes Monday's summary to `output/weekly_report/<date>_<run>/`
>
> Does that flow match what you want? Anything that goes somewhere else?

**Output path convention (always):**
- `output/<component_name>/<YYYY-MM-DD>_<run_description>/`
- Date first (sorts chronologically), then a short human-readable run label
- Never overwrite previous runs

**Input path convention (always):**
- `data/<source_name>/` — one subfolder per external source
- Named by the source (`data/zendesk_exports/`, `data/hubspot_contacts/`, `data/google_analytics/`)

**Every output has a home.** If a component generates something, it lands in `output/<component>/`. Don't leave this implicit.

---

### 6. Propose the project structure

*(Still within Step 2/7 — don't re-announce a new step number here.)*

Present a plain-language tree + rules summary. Get approval before moving on.

> Here's the folder layout I'll create:
>
> ```
> support_workflow/
> ├── CLAUDE.md                   (rules for Claude — including this structure)
> ├── README.md                   (one-page overview)
> ├── INITIAL.md                  (the project intent, component by component)
> ├── PRPs/                       (where implementation plans live)
> ├── .claude/                    (permissions + slash commands)
> │
> ├── components/                 (all the work lives here)
> │   ├── refresh_cli/            (pulls tickets from Zendesk)
> │   ├── ticket_insights/        (analyzes the tickets)
> │   └── weekly_report/          (generates Monday's summary)
> │
> ├── data/                       (inputs — organized by source)
> │   └── zendesk_exports/
> │
> └── output/                     (all artifacts — organized by component + date)
>     ├── ticket_insights/
>     └── weekly_report/
> ```
>
> **Rules I'll enforce in `CLAUDE.md`:**
> - Components live in `components/<name>/` — never loose at the project root
> - Inputs live in `data/<source>/` — never inside a component folder
> - Outputs go to `output/<component>/<date>_<description>/` — never overwriting prior runs
> - No new top-level folders without updating `CLAUDE.md`
>
> Want any of this different?

If they want changes (a different folder name, combining two components, etc.), adjust and re-propose.

---

### 7. Dispatch ce-researcher per component (parallel)

**Announce**:

> **Step 3/7 — Researching each component**
>
> Give me ~30 seconds to look into the best way to build each piece. You don't need to do anything.

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

**After all researchers return**, print a brief confirmation:

> Research complete. I looked at: {list of frameworks/topics, one line}.

---

### 8. Dispatch ce-planner

**Announce**:

> **Step 4/7 — Putting the design together**

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

### 9. Iterate

User may want changes. Refine and re-propose. Keep iterating until they say "go."

---

### 10. Ask for target path

Offer a sensible default:

> **Where should I create the project folder?**
>
> Common choices:
> - `~/projects/<project-name>` *(recommended — keeps all your projects organized together)*
> - `~/Documents/<project-name>`
> - Any other path you'd like
>
> Press enter for the default, or type your preferred path.

Accept relative or absolute paths. Expand `~` if present. If they press enter, use `~/projects/<slugified-project-name>`.

---

### 11. Scaffold

**Announce**:

> **Step 5/7 — Creating your project**
>
> Here's what I'm about to do:

Print a scaffolding manifest BEFORE files appear:

> ```
> Creating folder:           <target path>
>   ├─ CLAUDE.md              (rules for Claude — includes your project structure + component gotchas)
>   ├─ README.md              (one-page overview)
>   ├─ INITIAL.md             (pre-filled intent — one block per component)
>   ├─ PRPs/                  (where future plans will live)
>   ├─ .claude/
>   │    ├─ settings.local.json    (permissions)
>   │    └─ commands/              (/generate-prp, /execute-prp, /handoff)
>   ├─ components/
>   │    ├─ <component_1>/
>   │    ├─ <component_2>/
>   │    └─ <component_3>/
>   ├─ data/
>   │    └─ <source>/           (for your inputs)
>   ├─ output/
>   │    ├─ <component_1>/      (for its artifacts)
>   │    └─ <component_2>/
>   ├─ launch.[sh|command|bat]  (one-click Claude Code launcher for your OS)
>   └─ .gitignore
> ```
>
> Writing files now...

#### 11a. Main session writes the project-root skeleton

All sourced from **`deploy/`** unless noted. Treat `deploy/` as the canonical template; files outside `deploy/` stay in the kit.

1. **Create the target directory** and the folder skeleton:
   - `components/` (empty — ce-scaffold will fill per component)
   - `data/<source>/` for each declared input source (with `.gitkeep`)
   - `output/<component>/` for each component that produces artifacts (with `.gitkeep`)
   - `PRPs/`
   - `PRPs/archive/` (with `.gitkeep`) — `/execute-prp` moves completed PRPs here on success
   - `PRPs/source/` (with `.gitkeep`) — `/generate-prp` relocates `INITIAL.md` here after first successful run

2. **`.claude/settings.local.json`** — copy from `deploy/.claude/settings.local.json`.

3. **`.claude/commands/`** — copy all from `deploy/.claude/commands/` (`generate-prp.md`, `execute-prp.md`, `handoff.md`).

4. **`.gitignore`** — copy from `deploy/.gitignore`.

5. **Launch script** — detect OS and copy only the matching one:

   ```bash
   case "$(uname -s 2>/dev/null || echo Windows)" in
     Darwin*)               echo "macos" ;;
     Linux*)                echo "linux" ;;
     MINGW*|MSYS*|CYGWIN*)  echo "windows" ;;
     *)                     echo "unknown" ;;
   esac
   ```

   | Detected OS | File | Chmod |
   |---|---|---|
   | `macos` | `launch.command` | `chmod +x launch.command` |
   | `linux` | `launch.sh` | `chmod +x launch.sh` |
   | `windows` | `launch.bat` | (not needed) |
   | `unknown` | `launch.sh` (safe default) | `chmod +x launch.sh` |

6. **`PRPs/templates/prp_base.md`** + **`PRPs/README.md`** — copy both from `deploy/PRPs/`.

7. **`INITIAL.md`** — use `deploy/INITIAL.md` as the skeleton, but pre-fill with content from the conversation. One `## COMPONENT: <name>` block per component with its purpose, inputs, outputs, pattern, and any specific notes. See `deploy/INITIAL.md` for the exact shape.

8. **`README.md`** — a SHORT project README (one page max):
   - Project title + one-paragraph description
   - "Project structure" — copy the tree you showed in Step 6
   - "Components" — one line per component: name → purpose → pattern
   - "How to run" — the entry command per component (e.g., `streamlit run components/<name>/app.py`, `python components/<name>/scripts/run.py`)
   - "How to develop with Claude" — brief pointer to `/generate-prp INITIAL.md` → `/execute-prp` flow

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
- Any flags for shared dependencies

#### 11c. Build project CLAUDE.md dynamically

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

After CLAUDE.md is written, print:

> All files created.

---

### 12. Dispatch ce-validator

**Announce**:

> **Step 6/7 — Verifying everything looks good**

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
> stack: <project stack>
>
> Run validation and return a report.
> ```

Based on result:
- **PASS** → proceed to handoff
- **WARN** → minor issue. Either quickly patch before handoff OR mention to user ("I noticed X; it's minor, fix it in your first session")
- **FAIL** → blocker. Address, re-run validator.

---

### 13. Handoff

**Announce**:

> **Step 7/7 — Ready to go!**

Give clear, OS-specific next steps — show ONLY the instructions for the detected OS:

> Your project is ready at `<target path>`
>
> **For macOS** (if Darwin detected):
> > Double-click `launch.command` in the project folder to open Claude Code.
> >
> > *(First time only: if macOS warns "unidentified developer," right-click `launch.command` → Open.)*
> >
> > Or from Terminal:
> > ```
> > cd <target path>
> > ./launch.command
> > ```
>
> **For Windows**:
> > Double-click `launch.bat` in the project folder.
> >
> > Or from a terminal:
> > ```
> > cd <target path>
> > launch.bat
> > ```
>
> **For Linux**:
> > From a terminal:
> > ```
> > cd <target path>
> > ./launch.sh
> > ```
>
> When Claude Code opens, the project's `CLAUDE.md` loads automatically and `INITIAL.md` has all your components already specified. Your first move is usually `/generate-prp INITIAL.md` — that produces a single implementation plan covering all components in the right order.

**Do NOT** run anything in the scaffolded project from your current session. Your job ends here.

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

---

## Exit criteria

You're done when:
- Target folder exists with the full structure (components/, data/, output/, PRPs/, .claude/, CLAUDE.md, README.md, INITIAL.md, .gitignore, launcher)
- Every component has a populated `components/<name>/` folder with its own README.md
- The project's `CLAUDE.md` has the project-structure enforcement block + one component section per component + aggregated validation
- The user knows the exact next step (`cd <path> && claude` then `/generate-prp INITIAL.md`)

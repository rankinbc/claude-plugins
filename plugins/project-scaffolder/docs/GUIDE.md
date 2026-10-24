# Creating a project — a walkthrough

This is the full walkthrough for someone using `/new-project` for the first time. The [README](../README.md) has the short version; this one walks you through what you'll see at every step, what decisions you'll be asked to make, and what to do after the scaffold completes.

If you've scaffolded a project with this kit before, you probably don't need this doc.

---

## Before you begin

You need Claude Code installed and on your PATH. The `claude` command should work in a terminal. If it doesn't, follow the install instructions at [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code) and come back.

You do **not** need git, a GitHub account, or any cloud services. Scaffolded projects live on your laptop and don't upload anything anywhere.

You don't need a precise spec either. A rough paragraph describing what you want is enough — the interview fills in the rest.

---

## Step 1 — Open Claude Code in this folder

Open a terminal, `cd` into this kit folder, and run:

```
claude
```

You'll land in an interactive Claude Code session. The prompt is ready for your input.

---

## Step 2 — Run `/new-project`

Type:

```
/new-project
```

and press Enter. Claude will introduce the flow, then ask you to describe what you want to build.

From here you'll go through six phases. Most of them are automatic — you only have two approval moments.

### Phase 1 — The interview (≈2-4 minutes)

Claude asks what you want to build. Answer in plain language. A paragraph is plenty:

> *"I want something that pulls our monthly sales CSVs, finds trends by region, shows them in a dashboard, and emails a summary each month."*

Claude follows up with a few questions — things like: *How are the CSVs structured? What counts as a trend worth flagging? Who gets the report?* Answer as best you can. "Not sure, pick something reasonable" is a valid answer — Claude will pick a sensible default and you can change it later.

**You can re-scope at any point.** If you realize mid-interview that you want something different, just say so.

### Phase 2 — The component sanity check (one question)

Claude proposes a breakdown of your project into named components:

> *"I'll break this into 3 components: `ingestion`, `analysis`, `dashboard`. Sound right, or want a different breakdown?"*

Say **"yes"** (or "looks good", or just hit enter) to continue. If the breakdown feels off, say what's wrong — *"merge the first two"*, *"split the dashboard into two parts"*, *"actually I only want the analysis piece"* — and Claude will re-propose.

This is intentionally light. The goal is to catch the rare *"I meant 1 component, not 3"* moment before expensive research fires. It's not a design review.

### Phase 3 — Research (≈30-60 seconds, hands-off)

Claude dispatches a research agent per component, in parallel. You'll see something like:

> **Step 3/6 — Researching each component** *(back in ~30 seconds)*
> - `ingestion` → researching pandas + CSV parsing patterns
> - `analysis` → researching pandas time-series and anomaly detection
> - `dashboard` → researching Streamlit 1.31 + caching

Then wait. When research finishes, Claude prints a short summary of what each agent found — library versions, one key pattern per component, any gotchas worth flagging.

Nothing for you to do in this phase.

### Phase 4 — The unified proposal (your second approval)

Claude shows you the full design in one message:

- Where the project will be created (a path)
- What each component does, in plain language
- How the components connect (data flow)
- What tech it'll use (stack, one sentence)
- Any extra top-level folders (e.g. `mappings/`, `notebooks/`, `golden/`) that the research suggested
- Anything you should know up front (API keys needed, runs-on-laptop-only, etc.)

You have three options:

1. **Approve it** — "yes", "looks good", "go ahead". Scaffold begins immediately.
2. **Iterate** — "change the dashboard to use dash instead", "add a fourth component for X", "put it at `~/projects/sales` instead", "rename `analysis` to `insights`". Claude revises and re-shows.
3. **Start over** — "actually I want something completely different". You'll loop back to the interview.

The target path defaults to somewhere sensible under your home directory. You can change it in iteration.

### Phase 5 — Scaffold (≈30-60 seconds, hands-off)

Claude writes the entire project in parallel — one agent per component, each writing its own `components/<name>/` subfolder, plus all the project-level files (`CLAUDE.md`, `README.md`, `PRPs/`, `.claude/commands/`, `data/`, `output/`). Then the main session synthesizes your **v1 implementation plan** (the PRP) and writes it to `PRPs/v1_<slug>.md` — everything Claude needs to fill in the stubs with working code. A validator agent runs a structural check and reports back.

Transient scaffolder state (the manifest tracking lifecycle, first-run notes, optional auto-chain helper) lives in a hidden `.scaffolding/` folder. It will be auto-deleted later by `/execute-prp` on first successful build.

No input needed.

### Phase 6 — Handoff (one question)

Claude asks:

> **Ready to build?**
>
> I can launch your new project and kick off `/execute-prp PRPs/v1_<slug>.md` automatically — Claude will fill in the stubs with real code and run validation gates. Or say "not yet" if you want to review the scaffold + PRP first.

Two paths:

- **"yes"** → a new Claude Code window opens in your scaffolded project with `/execute-prp PRPs/v1_<slug>.md` already running. Skip to "After the scaffold" below.
- **"not yet"** → Claude prints the one-line command (`cd <project path> && claude`) for opening the project manually. Run it when you're ready.

If the auto-launch doesn't spawn a new window (depends on your OS and terminal setup), open a terminal yourself and run `cd <project path> && claude`, then type `/execute-prp PRPs/v1_<slug>.md`.

---

## After the scaffold — the PRP workflow

Your scaffolded project has two distinct workflows: **initial v1 build** (one command) and **post-build feature work** (three commands, starting with `INITIAL.md`).

### Initial v1 build — just `/execute-prp`

The scaffolder already wrote your implementation plan to `PRPs/v1_<slug>.md`. You don't need `/generate-prp` for the initial build — skip straight to:

```
/execute-prp PRPs/v1_<slug>.md
```

Claude reads the plan, fills in component stubs with real code, runs validation gates, and archives the PRP on success. It also **auto-deletes `.scaffolding/` and strips the status banner from README** — your project ends up clean, no scaffolder footprint left.

If you picked auto-chain at handoff, `/execute-prp` is already running when Claude Code opens. Just let it work.

**Worth doing once, after the build succeeds:** run `/run-skill-generator`. It gets your app running from a clean environment, captures what actually worked — install commands, env vars, the launch step — and commits it as a per-project skill under `.claude/skills/run-<name>/`. From then on `/run` and any agent in the repo follow that recipe instead of rediscovering it each session, and it only loads into context when something needs it. Most useful when starting a component takes more than the one command in your `CLAUDE.md` Components table — migrations, seeding, a service that has to be up first. Re-run it if the build or launch process changes.

### Adding a feature after v1 is built — `/generate-prp` → `/execute-prp`

Once v1 is built, new features use the standard PRP flow:

- **`/generate-prp`** — reads `PRPs/source/INITIAL.md` (your per-feature intake template — edit it in place to describe the new feature) and generates a detailed step-by-step build plan. Plan lands at `PRPs/<slug>.md`.
- **`/execute-prp PRPs/<slug>.md`** — runs the plan. Claude builds the feature, pauses at validation gates, and archives the PRP on success.

Trivial fixes (typos, one-line changes) don't need a PRP. Just ask Claude to do them directly.

### If you need to pause

Type `/handoff` at any time. Claude writes a `HANDOFF.md` capturing what's done, what's next, and any decisions made. When you come back later, open Claude Code in the project (`cd <project path> && claude`) and it'll pick up from there.

---

## Escape hatches

### "Walk me through each step"

If you want the old-style, fine-grained approvals (component names, data flow, folder tree, design, path — each approved separately), say so during the interview:

> *"Walk me through each step"* or *"Let me review each piece one at a time"*

Claude reverts to the step-by-step flow. Useful when you want to shape the design tightly.

### "I changed my mind"

At any approval moment, saying *"actually let's rethink this"* or *"start over"* loops you back to whichever phase makes sense. Nothing is committed until you approve the unified proposal in Phase 4.

### "The scaffold looks wrong"

If the scaffold finishes but something's off (missing component, wrong stack, etc.), you have two good options:

1. **Delete the folder and re-run `/new-project`** with a clearer ask. Nothing outside the project folder was changed.
2. **Open the project and ask Claude to fix it.** The scaffolded project's CLAUDE.md knows the structure; Claude can add components, rename things, or adjust the stack without a full re-scaffold.

---

## What a scaffolded project looks like

After the scaffold (pre-build, `.scaffolding/` still present):

```
<project>/
├── CLAUDE.md              # Rules Claude follows — structure, component index, validation
├── README.md              # What this project is, how to use it (includes a status banner)
├── pyproject.toml         # One dependency list + test config for every component
├── .env.example           # Secret key names — only if the project needs secrets
├── .scaffolding/          # Transient scaffolder state — auto-deleted by /execute-prp on build
│   ├── manifest.json      # Lifecycle tracker (stage: "plan" → "built") + component map
│   └── README.md          # First-run orientation + setup checklist
├── components/            # One subfolder per component, each with README.md + CLAUDE.md + code stubs
├── data/                  # Input data, organized by source
├── output/                # Where each component writes its results (logs included)
├── tests/                 # Project-wide tests, incl. a structural hygiene check
├── scripts/secure/        # Set-ProjectSecrets.ps1 + Test-Readiness.ps1 — only if the project needs secrets
├── PRPs/
│   ├── v1_<slug>.md       # Your v1 implementation plan — run /execute-prp on this
│   ├── source/INITIAL.md  # Blank per-feature template (for post-build feature work)
│   ├── templates/         # PRP template
│   └── archive/           # Completed PRPs land here
└── .claude/
    ├── settings.local.json   # Permissions, incl. deny rules that block Claude from your .env
    └── commands/          # /new-feature, /generate-prp, /execute-prp, /handoff, /deploy-status
```

Two things worth knowing about this layout:

**Each component carries its own `CLAUDE.md`.** Claude Code loads those on demand — only when Claude actually works in that folder. The root `CLAUDE.md` keeps a one-row-per-component index, so it stays about the same size whether the project has two components or six.

**Secrets live in one place and Claude can't read them.** All secrets go in a single gitignored `.env` at the project root, enforced two ways. `.claude/settings.local.json` denies the Read tool. Separately, a `PreToolUse` hook blocks any shell command that mentions the file — that second layer is the one that matters, because a permission deny list only blocks the exact commands you listed, while the allow list any usable project needs (`head`, `tail`, `grep`, `python`) leaves plenty of other ways to print a file. The hook runs before permission rules and overrides allow rules, so it closes the whole class rather than named instances.

To fill the file in, run `.\scripts\secure\Set-ProjectSecrets.ps1` **in your own terminal**; it prompts for each key with the input hidden. Claude Code runs commands with stdin closed, so it can't drive that script even if asked. Claude can run `Test-Readiness.ps1`, which reports which keys are set — by name, never by value.

After a successful `/execute-prp PRPs/v1_<slug>.md`:

- `.scaffolding/` is deleted entirely
- The status banner in `README.md` is stripped
- `PRPs/v1_<slug>.md` is moved to `PRPs/archive/<date>_v1_<slug>.md`
- Component stubs are replaced with real, working code

The project is now clean — zero scaffolder cruft, ready to be used for its original purpose.

To re-open Claude Code in the project later: `cd <project path> && claude`.

---

## Common questions

**Do I need git?** No. Scaffolded projects are not git repos by default. If you want one, `git init` in the project folder yourself.

**Does this upload my code anywhere?** No. Everything is local. Claude Code talks to Anthropic's API to think, but no project files are stored remotely.

**Can I use this with an existing project?** Not directly — `/new-project` is for new projects. For existing work, copy the parts you want (the `.claude/commands/` folder, the `CLAUDE.md`, `PRPs/` scaffolding) into your own repo manually.

**Can Claude pick the stack for me?** Yes — in the interview, say *"pick a reasonable stack"* and Claude will choose based on your components (typically Python for analysis/reporting, Node or Python for APIs).

**Can I change the stack later?** Yes. Edit `PRPs/source/INITIAL.md` with a note like *"switch the dashboard to use dash instead of Streamlit"* and run `/generate-prp`. The new PRP will handle the migration.

**Why did `.scaffolding/` disappear after my first build?** `/execute-prp` auto-deletes it on successful v1 build — the manifest and first-run notes are scaffolder-specific, not part of your project. The same success pass strips the status banner from README.md and archives the v1 PRP. You end up with a clean project containing only the files and folders your work actually needs.

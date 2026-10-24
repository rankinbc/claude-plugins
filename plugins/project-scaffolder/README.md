# project-scaffolder

**Version 2.1** — a Claude Code plugin that scaffolds `scaffold_version: 2` projects. See [What's new in 2.1](#whats-new-in-21) and [What's new in 2.0](#whats-new-in-20).

A scaffolder for new Claude Code projects. Instead of opening Claude Code in an empty folder and hoping it figures out a sensible structure, you run `/project-scaffolder:new-project`, answer a few questions, and end up with a fully researched, organized, plan-driven project ready to build.

For the actual how-to-run-it, see [QUICK-START.md](QUICK-START.md). This doc is about *what it does* and *why you'd use it*.

## Install

Inside Claude Code:

```
/plugin marketplace add rankinbc/claude-plugins
/plugin install project-scaffolder@rankinbc
```

Start a new Claude Code session afterwards — plugins load at startup.

---

## Why use it

Open Claude Code in an empty folder and say *"build me a dashboard"* and Claude starts typing immediately. For a throwaway script, fine. For anything with multiple components, real data flow, or work you'll come back to next week, things drift fast:

- **Claude wings the setup.** Stack and folder layout picked on the fly. Sometimes reasonable, sometimes not — and the next session may pick differently.
- **Decisions evaporate across sessions.** A choice from Monday gets quietly reversed on Friday.
- **No plan to check against.** Hard to tell what's done, what's left, or whether Claude actually understood the ask.
- **No conventions.** Tests exist or they don't. Style drifts. Files land wherever.
- **Resuming hurts.** A week later, Claude is re-learning your project from whatever's in the code.
- **Temp files everywhere.** Single-use scripts, scratch outputs, and `notes.md` files accumulate at the root with no cleanup story.

This plugin front-loads the structure that prevents all of that *before any code is written*.

---

## What it does

`/project-scaffolder:new-project` runs a short guided interview (~4-7 minutes), then:

1. **Decomposes** your idea into named components, each matched to a proven pattern.
2. **Researches** each component in parallel — picks libraries based on what works today, surfaces known gotchas.
3. **Proposes** a project structure for you to approve before anything is written.
4. **Scaffolds** the full project: folder layout, component stubs, conventions, slash commands, and a v1 implementation plan.
5. **Hands off** with the exact command to reopen Claude Code inside your new project, where `/execute-prp PRPs/v1_<slug>.md` builds it.

---

## What you get

### At scaffold time

- **A short adaptive interview** that makes you articulate the project before any code is written.
- **Parallel per-component research** via sub-agents — library choices grounded in what works today, gotchas surfaced up front.
- **A multi-component design proposal** you approve before scaffolding starts.
- **A v1 implementation PRP** (Project Requirements Plan) written directly at scaffold time — step-by-step build instructions with validation gates. No intermediate `/generate-prp` step needed for the initial build.
- **A standard folder layout** — `components/<name>/`, `data/<source>/`, `output/<component>/<date>_<description>/`. Same shape every time, so you always know where things live.
- **Pattern-based component shapes**: dashboard, API, analysis, CLI, tracker, report, automation, form-view, integration, product-doc, research. Each pattern encodes what a working component of that shape looks like.
- **Post-scaffold structural validation** — a sub-agent checks the scaffold passes its own enforcement rules before you start building.
- **No scaffolder footprint left behind** — all transient state lives in `.scaffolding/` and auto-deletes on first successful build.

### In every scaffolded project

- **A root `CLAUDE.md` with enforcement rules** — context discipline (scout before reading large files, sample data instead of slurping it, dispatch sub-agents, externalize plans), code conventions (file size limits, organize by feature), testing defaults, doc upkeep, project cleanliness (output rotation, descriptive names, no rogue top-level folders), PRP workflow defaults. It holds a one-row-per-component index, so it stays about the same size whether you have two components or six.
- **A `CLAUDE.md` inside each component** — that component's pattern gotchas and I/O paths. Claude Code loads these on demand, only when it actually works in that folder, so they cost nothing the rest of the time.
- **Secrets kept out of the conversation** — one gitignored `.env` at the project root. `permissions.deny` blocks the Read tool, and a fail-closed `PreToolUse` hook stops shell, file and search calls that reach for it (case, quotes, wildcards and recursive `grep` included) — a guardrail against accidental reads, not a sandbox. That second layer matters because a normal allow list hands out a dozen ways to read a file (`head`, `grep`, `python -c`) and a deny list only ever blocks the spellings you thought of. `scripts/secure/Set-ProjectSecrets.ps1` prompts you for each key with the input hidden; `Test-Readiness.ps1` tells Claude which keys are set, by name only.
- **One dependency manifest, one environment** — every component's deps in the root `pyproject.toml`, installed once. No per-component `requirements.txt` to drift.
- **Validation gates tuned for long sessions** — pytest and ruff configured for compact output, because `/execute-prp` runs them repeatedly against failing code and every extra line costs context.
- **A structural hygiene test** — `tests/test_repo_hygiene.py` enforces the 500-line file limit and the no-artifacts-at-root rule that `CLAUDE.md` declares, so those rules can't quietly decay.
- **`/execute-prp`** — runs any PRP with validation gates at each checkpoint, atomic commits, and PRP archival on success.
- **`/new-feature`** — guided interview for post-build feature work; mirrors `/new-project` but scoped to one feature, then chains into `/generate-prp` → `/execute-prp`.
- **`/generate-prp`** — researches and writes a PRP from `PRPs/source/INITIAL.md` for any new feature.
- **`/deploy-status`** — read-only report of what's built, what's still a stub, and the exact next command to run.
- **`/handoff`** — pause cleanly mid-work; the next session picks up without re-explaining.
- **PRP lifecycle baked in** — active plans in `PRPs/`, completed ones archived to `PRPs/archive/<date>_<slug>.md` automatically.
- **Per-feature intake template** — `PRPs/source/INITIAL.md` for spec'ing the next feature.
- **Language-agnostic defaults** — Python, Node, Go, Rust, .NET, Ruby, etc. work out of the box. Stack-specific rules append cleanly to `CLAUDE.md`.

---

## What's new in 2.1

- **Installs as a plugin.** No more cloning the kit and running Claude Code inside it. Install once from the `rankinbc` marketplace and run `/project-scaffolder:new-project` from any empty folder.
- **Scaffolds where you are.** The new project lands in the folder you started Claude Code in (or in a `<project-name>/` subfolder if that folder isn't empty). You can still pick another path during the design review.
- **Same output.** Scaffolded projects are unchanged: still `scaffold_version: 2`, with the same files and slash commands.

---

## What's new in 2.0

Version 2 changes the shape of what gets scaffolded. The three-step flow you run is identical — `/new-project`, `cd` into the project, `/execute-prp` — but the project it produces is different enough that the manifest records it as `scaffold_version: 2`.

- **Per-component `CLAUDE.md` files.** Component gotchas moved out of the root `CLAUDE.md` and into `components/<name>/CLAUDE.md`, which Claude Code loads only when working in that folder. Previously the root file grew with every component and every session paid for all of them.
- **Secrets consolidated and locked.** One `.env` at the project root instead of one per component, so a key shared by three components is entered once. `permissions.deny` blocks Claude from reading it — a client-enforced rule, not a convention — and a PowerShell script populates it without any value passing through a conversation.
- **One environment, one install.** Dependencies moved from per-component manifests to a single root `pyproject.toml`. First-run setup is one install command instead of one per component.
- **Cheaper validation loops.** pytest and ruff ship configured for compact output. Measured on a small failing test suite: 39% less pytest output and 61% less ruff output, with nothing actionable lost.
- **Rules that enforce themselves.** A hygiene test now checks the file-size and artifact-placement rules that `CLAUDE.md` previously only stated.

Projects scaffolded with version 1 keep working — each one carries its own copy of the slash commands from the day it was created. There's no migration step, and none is needed.

---

## What a "PRP" is

A Project Requirements Plan: a structured plan Claude generates from your project description. Breaks work into concrete steps with validation gates, so Claude knows exactly what to build, in what order, and how to verify it's done right. The v1 PRP is the build plan for your initial project; subsequent PRPs cover individual features added later. They're the spine of the workflow — the thing that keeps Claude on plan across long sessions and context resets.

---

## How to use it

Install the plugin (above), open Claude Code in an empty folder, run `/project-scaffolder:new-project`, and follow the prompts. For the full step-by-step walkthrough, see [QUICK-START.md](QUICK-START.md). For a longer narrative guide, see [docs/GUIDE.md](docs/GUIDE.md).

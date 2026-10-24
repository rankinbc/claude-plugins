# Quick Start

A scaffolder for creating new Claude Code projects. Run one command, answer a few questions, Claude does research on the topic of your project, and sets up a fully structured project with an organized folder layout, conventions, organization rules, executable build plan, and built-in workflow system (PRP workflow) for adding new features in an organized, context-smart way —

**Why use it:** opening Claude Code in an empty folder and prompting *"build me X"* leads to drift fast — Claude picks a stack on the fly, conventions get invented and forgotten, no plan to check against, temporary one-off files everywhere. This kit front-loads the structure that prevents all of that.

---

## Step 1 — Scaffold

Open claude in this directory (claude-project-scaffolder)
 
 type:

```
/new-project
```

Claude runs a short interview (~4-7 minutes), researches your components in parallel, proposes a structure for you to approve, and scaffolds the full project: folder layout, component stubs, a `CLAUDE.md` with enforcement rules, and a complete implementation plan at `PRPs/v1_<slug>.md`.

---

## Step 2 — Open Claude in a new window in the newly created directory

When `/new-project` finishes, it prints the exact command to reopen Claude Code in your new project:

```
cd <path-to-new-project> && claude
```

Run it. Fresh session, now inside the scaffolded project.

---

## Step 3 — Build it

Type:

```
/execute-prp PRPs/v1_<slug>.md
```

Claude works through the plan step by step, fills the component stubs with real code, runs validation gates at each checkpoint, and on success auto-deletes `.scaffolding/` — leaving your project clean, functional, and ready to use.

---

## That's it

You now have a fully functional project ready to use. It is researched, organized, and in a folder structure that makes sense. It will stay maintained and follow strict organizational rules. From here, your scaffolded project ships with extra commands for ongoing work — `/new-feature` for guided feature additions, `/deploy-status` for state checks, `/handoff` for clean session pauses. See the project's own `README.md` for those.

For the longer walkthrough, see [docs/GUIDE.md](docs/GUIDE.md).

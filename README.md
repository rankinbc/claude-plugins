# claude-prp-scaffold

Deploy complex multi-component projects by having a brief interview with Claude. After answering a few questions, research is done on each component in parallel, then the project is scaffolded out in an organized, consistent way — every project is context-smart, follows a built-in plan-and-execute workflow, and is structured to stay coherent across long sessions.

---

## Why this is different from starting a project normally

A project deployed using this kit has structure built in from the start — a clear intake doc, a generated plan Claude follows step by step, standardized rules for how code is written and organized, and a workflow designed to survive long sessions without losing context. Instead of Claude winging it from a vague prompt, it works from a verified plan with checkpoints.

---

## Features

Projects scaffolded with this kit:

- Start from a guided interview that decomposes your idea into named components
- Research each component in parallel before writing a single file
- Scaffold a fully structured workspace automatically from proven pattern shapes (dashboard, API, analysis, CLI, tracker, report, automation, and more)
- Generate a detailed Project Requirements Plan from your intent doc with `/generate-prp`
- Execute that plan step by step with validation gates via `/execute-prp`
- Inject standardized coding, testing, and cleanliness rules into every project via `CLAUDE.md`
- Resume long sessions cleanly with `/handoff` — no lost context
- Support any language stack out of the box (Python, Node, Go, Rust, .NET, Ruby, and more)

---

## What is a PRP?

A PRP (Project Requirements Plan) is a structured plan Claude generates from your project description. It breaks work into concrete steps with validation gates — so Claude knows exactly what to build, in what order, and how to verify it's done right.

---

## Usage

1. Open Claude Code in your project folder
2. Run `/new-project` and answer a few questions
3. Claude scaffolds your workspace and writes a plan
4. In the newly deployed folder, run `/execute-prp` and start building

---

## Example: Sales Data Dashboard

1. Open Claude Code in an empty folder
2. Run `/new-project`
3. Claude asks what you want to build — you say: "I want something that pulls in our monthly sales CSVs, cleans them up, analyzes trends by region, shows it all in a dashboard, and emails a summary report to the team every month"
4. Claude asks a few follow-up questions: How are the CSVs structured? What counts as a trend worth flagging? Should the dashboard be interactive or static? Who receives the report and in what format?
5. Claude proposes a structure — `ingestion` to clean and normalize the raw files, `analysis` to calculate regional trends and flag anomalies, `dashboard` for the interactive web UI, and `report` to generate and email the monthly summary — then shows you the full plan before writing anything
6. You approve, Claude scaffolds the full project: folder structure, a filled-in `INITIAL.md`, and a generated PRP with step-by-step build instructions
7. Run `/execute-prp PRPs/sales-dashboard.md` — Claude works through the plan, builds the code, and validates each step
8. Your full system is ready — drop in a CSV and it runs through the pipeline, results appear in the dashboard, and the monthly summary is generated and emailed automatically. The project is structured, context-smart, and has a built-in workflow so you can keep building on it without starting from scratch each session.

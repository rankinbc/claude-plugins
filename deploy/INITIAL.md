<!--
  INITIAL.md — the intent doc that drives /generate-prp.

  This project has one or more **components**. Each component is a named,
  purposeful piece of work (an analysis, a CLI, a report, etc.). Claude fills
  a block for each one during /new-project.

  Fill each section with real detail. The more concrete, the better the PRP.

  Not sure what to put here? Describe the feature out loud to Claude —
  just say what you want to build and let Claude ask clarifying questions.
  When the spec feels solid, update the sections below and run
  /generate-prp INITIAL.md.

  Delete these hint comments when you're done — or leave them; they're ignored
  when Claude reads the file.
-->

## PROJECT

<!--
  One paragraph describing the overall goal of the project — what it lets
  you do that you couldn't do before. Not component-level detail; that's
  in the COMPONENT blocks below.
-->

[Overall project goal in one paragraph]


## COMPONENTS

<!--
  One block per component. Keep the headers exactly as shown — /generate-prp
  parses them to plan each component.

  Pattern refers to the shape file (dashboard, analysis, report, cli, etc.).
-->

### COMPONENT: <component_name_1>

**Pattern**: <pattern file, e.g., `analysis.md`>

**Purpose**: [What this component does, in 1-2 sentences]

**Inputs**: [Where it reads from — e.g., `data/<source>/` — or "None"]

**Outputs**: [Where it writes to — e.g., `output/<component>/<date>_<run>/` — or "None"]

**Notes**: [Component-specific considerations — edge cases, gotchas, constraints]


### COMPONENT: <component_name_2>

**Pattern**: <pattern file>

**Purpose**: ...

**Inputs**: ...

**Outputs**: ...

**Notes**: ...


## SHARED DOCUMENTATION

<!--
  Links Claude should pull in while designing. Include:
    - Official docs for any library/framework used across components
    - API reference URLs for any external service called
    - MCP servers relevant to this work
    - Internal wiki / design-doc links (Claude can't read these, but noting
      them helps you remember to paste the relevant content in)

  Be specific about which section of a doc matters — "FastAPI docs, especially
  the Dependency Injection section" is more useful than "FastAPI docs."
-->

[List shared documentation links here]


## OTHER CONSIDERATIONS

<!--
  The highest-value section. Things AI assistants typically miss about YOUR
  project go here:
    - "This codebase uses tabs, not spaces"
    - "We never use async for database calls — legacy reasons"
    - "Rate limit is 10 req/sec on this API, not the documented 100"
    - "If you touch auth, re-read CLAUDE.md's security section first"
    - "The previous attempt at this failed because <X>; don't repeat it"

  Also: project-wide edge cases, failure modes, gotchas specific to your
  domain that span components. Component-specific gotchas belong in the
  component's Notes field above.
-->

[Project-wide considerations]

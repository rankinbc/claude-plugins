# Shape: Product Document

PRDs, one-pagers, launch briefs, retros, design docs — structured product writing where the output is a document, not code.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/, the single `pyproject.toml`, and the single `.env`) lives at the project root.

## Default stack

- **Markdown** as the authoring format (renders in GitHub, Confluence, Notion, etc.)
- **Python (optional)** + `pandoc` if the user wants PDF/DOCX export
- **Frontmatter** for metadata (status, owner, date)

No runtime. Output is a file.

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                 # Purpose / inputs / outputs / how to run (ce-scaffold writes it)
├── CLAUDE.md                 # Pattern gotchas, lazy-loaded (ce-scaffold writes it)
├── templates/
│   ├── prd.md                # Blank PRD template
│   ├── one_pager.md          # Short summary doc
│   └── launch_brief.md       # Launch announcement
├── drafts/                   # Work-in-progress documents
│   └── .gitkeep
└── export.py                 # OPTIONAL: markdown → PDF via pandoc
```

Published documents (reviewed and shared) land in `output/<component_name>/<YYYY-MM-DD>_<doc_slug>/` at the project root. Reference material (prior docs, research) lives in `data/<source_name>/` at the project root.

## Starter files

> **`product_doc` is a special case:** the deliverable is the markdown itself. ce-scaffold *does* ship the section-header skeleton below (it IS the work product's shape), but leaves each section body as `[/execute-prp fills this in based on PRPs/source/INITIAL.md]`. No executable code ships — there's nothing to execute.

**`templates/prd.md`** — a real PRD skeleton worth shipping:

```markdown
---
title: {Feature Name}
author: {Your name}
status: draft | review | approved | shipped
date: {YYYY-MM-DD}
stakeholders: [{PM}, {Eng lead}, {Design}]
---

# {Feature Name} — PRD

## TL;DR

{One paragraph: what we're building, for whom, and why it matters. An exec should be able to approve the project from this alone.}

## Problem

{What's broken / missing / frustrating. Who feels the pain. How often. Evidence (metrics, research, support tickets).}

## Goal

{What success looks like. 1-3 measurable outcomes. Tie to business metrics where possible.}

## Users

{Primary user segment. Secondary users if any. What they do today vs. what they'd do with this.}

## Solution

{What we're building, at a high level. Not implementation details. User-visible behavior.}

### Key interactions
1. User does X → system responds with Y
2. ...

### What's in scope
- ...

### What's out of scope (explicit non-goals)
- ...

## Success metrics

- **Primary**: {metric} from {current baseline} to {target} by {date}
- **Secondary**: {metric}
- **Guardrails**: {metrics we don't want to regress — e.g., latency, churn}

## Risks & assumptions

- **Assumption**: {something we believe but haven't validated}
- **Risk**: {what could go wrong} → **Mitigation**: {how we'd handle it}

## Alternatives considered

- **Option A**: {brief} — rejected because {reason}
- **Option B**: {brief} — rejected because {reason}

## Open questions

- {Things we still need to decide, with owner and deadline}

## Timeline (rough)

- {Milestone 1}: {date}
- {Milestone 2}: {date}
- Launch: {date}

## Appendix

{Data, research links, mocks, supporting material}
```

**`templates/one_pager.md`** — when full PRD is overkill:

```markdown
---
title: {Name}
author: {You}
date: {YYYY-MM-DD}
---

# {Name}

**What**: {One sentence}
**Why**: {One sentence on the problem or opportunity}
**Who it's for**: {User segment}
**How we'll measure success**: {One metric}

## Background

{2-3 sentences}

## Proposal

{3-5 bullets}

## What we're NOT doing (explicit)

- ...

## Next step

{Single concrete action — who, by when}
```

**`templates/launch_brief.md`** — for announcements:

```markdown
---
title: {Feature} — Launch Brief
launch_date: {YYYY-MM-DD}
---

# {Feature} Launch

## What launched
{One sentence}

## Who it's for
{User segment; call out any limits like "available on iOS only" or "beta"}

## Why it matters
{Business impact or user value in plain terms}

## How to talk about it

- **For customers**: {1-2 sentence pitch}
- **For prospects**: {1-2 sentences for sales}
- **For internal teams**: {what support/CS need to know}

## Metrics to watch

- ...

## Known limitations / what's not in v1

- ...

## Support + escalation

- Owner: {name}
- Escalation path: {Slack channel, email}
```

**`scripts/export.py`** (optional — for PDF export):

```python
"""Export a markdown doc to PDF via pandoc.

Usage (from project root):
    python components/<component_name>/export.py components/<component_name>/drafts/prd-feature-x.md
"""
import subprocess
import sys
from pathlib import Path
from datetime import date

COMPONENT_DIR = Path(__file__).parent
PROJECT_ROOT = COMPONENT_DIR.parent.parent
COMPONENT_NAME = COMPONENT_DIR.name

def main():
    if len(sys.argv) != 2:
        print("Usage: python components/<component_name>/export.py <path-to-markdown>")
        sys.exit(1)

    md = Path(sys.argv[1])
    if not md.exists():
        print(f"Not found: {md}")
        sys.exit(1)

    out_dir = PROJECT_ROOT / "output" / COMPONENT_NAME / f"{date.today().isoformat()}_{md.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f"{md.stem}.pdf"
    # Also copy the markdown alongside the PDF so the published doc is self-contained
    (out_dir / md.name).write_text(md.read_text())

    subprocess.run(["pandoc", str(md), "-o", str(pdf), "--pdf-engine=weasyprint"], check=True)
    print(f"Written: {pdf}")

if __name__ == "__main__":
    main()
```

## How to run

Most of the work is writing. Running happens only if exporting.

From the project root:

```bash
# Edit drafts in components/<component_name>/drafts/ — pure markdown, any editor
# For PDF export (optional — requires pandoc + weasyprint or wkhtmltopdf):
python -m pip install -e ".[dev]"   # inside the project venv
python components/<component_name>/export.py components/<component_name>/drafts/prd-feature-x.md
# Published PDF + markdown copy lands in output/<component_name>/<date>_<doc_slug>/
```

## Gotchas for CLAUDE.md

- **TL;DR at the top, always.** An executive should be able to approve or reject the doc by reading only the TL;DR. The details are for those who dig in.
- **Front-load the ask.** What decision does this doc need? State it plainly before context.
- **Write for the audience.** PRD for engineers is different from one-pager for execs. Ask who reads this before writing.
- **Name non-goals explicitly.** "We are NOT building X in v1" prevents scope creep and stakeholder confusion.
- **Metrics with numbers, not adjectives.** "Faster" is not a success metric. "p95 latency < 200ms" is.
- **Cite evidence.** "Users want this" → who said it, in what context, how many. Link support tickets, research, data.
- **Don't pre-commit to implementation.** PRDs describe user-visible behavior, not technical architecture. That's engineering's call.
- **Versioning matters.** Keep old versions in `output/<component_name>/<date>_<slug>/` — the date-stamped folders ARE the version history. When a PRD changes, explain what changed and why.

## Validation

```bash
# Markdown lint (optional but nice)
markdownlint components/<component_name>/**/*.md

# Dead link check (optional)
markdown-link-check output/<component_name>/*/*.md

# Spellcheck (optional)
aspell check components/<component_name>/drafts/prd-feature-x.md
```

For document quality, validation is mostly manual — ask a second pair of eyes before "published."

## INITIAL.md pre-fill hints

- **FEATURE**: What document(s) do they need? (PRD, one-pager, launch brief, retro, design doc). For whom. About what.
- **EXAMPLES**: Past PRDs or docs they liked? Their team's template preferences?
- **DOCUMENTATION**: Any stakeholder frameworks to follow (RICE scoring, OKRs, etc.)
- **OTHER CONSIDERATIONS**: Audience technical level. Doc length expectation. Stakeholders who must approve. Deadline.

## Interview follow-ups

- "What's the doc for — a decision, an announcement, a retrospective?"
- "Who reads it — exec team, eng team, customers, cross-functional?"
- "Is there a template your company uses, or are we starting fresh?"
- "How long — one page, ten pages, in-between?"
- "Do you need to export to PDF/DOCX, or is markdown enough?"
- "Any past docs from your team I should model the voice/structure on?"

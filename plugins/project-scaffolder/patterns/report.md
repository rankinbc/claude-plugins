# Shape: Recurring Report

Weekly / monthly / quarterly reports combining data + narrative. Different from one-off `analysis.md` (which produces a single artifact) — this is infrastructure for reports that get regenerated on a cadence, with the same structure each time.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/, the single `pyproject.toml`, and the single `.env`) lives at the project root.

## Default stack

- **Python 3.11+** + pandas
- **Jinja2** for report templating (narrative structure + data placeholders)
- **matplotlib** for charts (embedded as PNGs)
- Optional: **cron / Task Scheduler / GitHub Actions** for auto-generation
- Output: markdown (primary) with embedded chart images

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                   # Purpose / inputs / outputs / how to run (ce-scaffold writes it)
├── CLAUDE.md                   # Pattern gotchas, lazy-loaded (ce-scaffold writes it)
├── templates/
│   └── report.md.j2            # Jinja template — the structural skeleton
├── generate.py                 # Loads data, renders template, saves output
└── config.yaml                 # Metric definitions, report cadence, audiences
```

Input data (CSV from API export, DB query dumps, etc.) lives in `data/<source_name>/` at the project root. Each rendered report lands in `output/<component_name>/<YYYY-MM-DD>_<run_description>/` with the report.md and charts/ subfolder.

## Starter files

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (a 3-line skeleton template + a trivial render script + a TODO marker). The files below are the implementation target `/execute-prp` uses during the build stage — matching the structure, sections, and constraints shown.

**`templates/report.md.j2`** — the structural template (Jinja):

```jinja
# {{ report_title }} — {{ report_date }}

## TL;DR

{{ tldr }}

## Headline metrics

| Metric | This period | Last period | Change |
|---|---|---|---|
{% for m in headline_metrics %}| {{ m.name }} | {{ m.current }} | {{ m.previous }} | {{ m.change }} |
{% endfor %}

## What happened this period

{{ narrative }}

## Charts

{% for chart in charts %}
### {{ chart.title }}

![{{ chart.title }}](charts/{{ chart.filename }})

{{ chart.caption }}

{% endfor %}

## Flags / things to watch

{% for flag in flags %}
- **{{ flag.metric }}**: {{ flag.description }}
{% endfor %}

## Next period focus

{{ next_period_focus }}

---

*Generated {{ report_date }} by `scripts/generate.py`. Source data: `data/`.*
```

**`generate.py`** — minimal runnable skeleton:

```python
"""Generate a recurring report.

Usage (from project root):
    python components/<component_name>/generate.py                  # Uses today's date
    python components/<component_name>/generate.py --date 2025-01-15   # Backfill a specific date
"""
import argparse
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import yaml
from jinja2 import Template

COMPONENT_DIR = Path(__file__).parent
PROJECT_ROOT = COMPONENT_DIR.parent.parent
COMPONENT_NAME = COMPONENT_DIR.name
# Adjust <source_name> to match your data source
DATA_DIR = PROJECT_ROOT / "data" / "<source_name>"


def load_config() -> dict:
    return yaml.safe_load((COMPONENT_DIR / "config.yaml").read_text())


def load_data() -> pd.DataFrame:
    # TODO: replace with actual data loading (CSV, API call, DB query)
    data_files = list(DATA_DIR.glob("*.csv"))
    if not data_files:
        raise FileNotFoundError(f"Drop a data file in {DATA_DIR} to begin")
    return pd.read_csv(data_files[0])


def compute_metrics(df: pd.DataFrame, config: dict) -> list[dict]:
    """Compute the headline metrics. Customize per report."""
    # TODO: replace with real metric calculations
    return [
        {"name": "Example metric", "current": 100, "previous": 90, "change": "+11%"},
    ]


def render_charts(df: pd.DataFrame, out_dir: Path) -> list[dict]:
    """Produce charts as PNGs; return metadata for the template."""
    out_dir.mkdir(parents=True, exist_ok=True)
    charts = []

    fig, ax = plt.subplots()
    df.plot(ax=ax)
    path = out_dir / "trend.png"
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)

    charts.append({
        "title": "Example trend",
        "filename": "trend.png",
        "caption": "One sentence explaining what the chart shows.",
    })
    return charts


def build_narrative(metrics: list[dict], charts: list[dict]) -> str:
    """Generate the prose commentary. Start simple; iterate to make it better."""
    return "This period's narrative goes here. Replace with real analysis."


def main(report_date: date) -> None:
    config = load_config()
    df = load_data()

    run_dir = PROJECT_ROOT / "output" / COMPONENT_NAME / f"{report_date.isoformat()}_{config['report_slug']}"
    charts_dir = run_dir / "charts"

    metrics = compute_metrics(df, config)
    charts = render_charts(df, charts_dir)
    narrative = build_narrative(metrics, charts)

    context = {
        "report_title": config["report_title"],
        "report_date": report_date.isoformat(),
        "tldr": "Replace with 2-3 sentences that let an exec close the report after reading just this.",
        "headline_metrics": metrics,
        "narrative": narrative,
        "charts": charts,
        "flags": [],
        "next_period_focus": "What to watch / do differently next period.",
    }

    template = Template((COMPONENT_DIR / "templates" / "report.md.j2").read_text())
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.md").write_text(template.render(**context))
    print(f"Report written: {run_dir / 'report.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                        default=date.today())
    args = parser.parse_args()
    main(args.date)
```

**`config.yaml`** — report metadata:

```yaml
report_title: "Weekly Product Metrics"
report_slug: "weekly_metrics"
cadence: weekly     # weekly | monthly | quarterly
audience: "Product team + exec staff"

# Metric definitions — central so they stay consistent across runs
metrics:
  - name: "Weekly active users"
    source: "data/analytics.csv"
    column: "wau"
  # ...

# What "a bad week" looks like — flags get surfaced in the report
guardrails:
  - metric: "p95_latency_ms"
    threshold_max: 500
  # ...
```

**Project-level dependencies** — these go in the root `pyproject.toml` under `[project] dependencies`, never a component-local manifest:
```
pandas>=2.0
matplotlib>=3.8
jinja2>=3.1
pyyaml>=6.0
```

## How to run

From the project root:

```bash
pip install -e .
# Drop data file in data/<source_name>/
python components/<component_name>/generate.py
# Report lands at output/<component_name>/<date>_<slug>/report.md
```

To schedule (weekly on Mondays at 8am):

```cron
0 8 * * 1 cd /path/to/project && /path/to/venv/bin/python components/<component_name>/generate.py >> output/<component_name>/cron.log 2>&1
```

## Gotchas for CLAUDE.md

- **TL;DR at the top, always.** Exec reading on their phone should be able to close the tab after two sentences. Details come after.
- **Metric definitions live in config.yaml, not scattered across scripts.** If "DAU" means different things in different places, reports lie. One definition, referenced by all.
- **Dated output folders.** `reports/weekly_metrics_2025-01-15/` — not `reports/latest/`. Old reports stay; history is the point of a recurring report.
- **Guardrail metrics matter.** Reports that only show the primary metric hide problems. Include latency, churn, cost, whatever must NOT regress.
- **Compare to last period explicitly.** A metric alone is noise; with delta vs. last period it's signal.
- **Flags > alarms.** Note what warrants attention, don't scream. Reader decides severity.
- **Don't hide nulls/drops.** If data for a segment is missing this period, say so — don't silently zero it out.
- **Fiscal calendars differ.** "Weekly" could mean ISO week, company week, or calendar week. Pick one; document it in config.yaml.
- **Charts need captions.** Every chart says what the reader should see. Don't make them interpret.
- **Timezone in the filename and in the report.** "Weekly report 2025-01-15" — which timezone? UTC? User-local? Document it.

## Validation

```bash
# Lint
python -m ruff check components/<component_name>/

# Smoke test
python components/<component_name>/generate.py
ls output/<component_name>/*/report.md >/dev/null && echo "Report generated"

# Template parses (catches Jinja syntax errors)
python -c "from jinja2 import Template; Template(open('components/<component_name>/templates/report.md.j2').read()).render(report_title='x', report_date='2025-01-01', tldr='x', headline_metrics=[], narrative='x', charts=[], flags=[], next_period_focus='x')"
```

## Project-level footprint

- `templates/` — shared Jinja/HTML report layouts when the project has multiple reports that should look consistent. A project with only one report component usually doesn't need this (the component's own `templates/` folder is enough).

## INITIAL.md pre-fill hints

- **FEATURE**: What report (weekly metrics, monthly exec, quarterly retro). Who the audience is. What metrics / sections.
- **EXAMPLES**: Prior reports they produced (even informally). Any templates they've seen and liked.
- **DOCUMENTATION**: Data source docs (analytics tool, DB schema). Company's metric definitions wiki if one exists.
- **OTHER CONSIDERATIONS**: Cadence. Automation vs. manual. Distribution (email, Slack, Confluence). Historical retention. Anyone who must review before distribution.

## Interview follow-ups

- "What's the report cadence — weekly, monthly, quarterly, something else?"
- "Who reads it — your team, exec, company-wide, external?"
- "What are the 3-5 headline metrics that tell the story?"
- "What data sources — spreadsheet, database, analytics tool (Mixpanel / GA / Amplitude), API?"
- "Do you want this to run automatically on a schedule, or only when you ask?"
- "Where does the finished report go — email, Slack, Confluence, just a file?"
- "What's a 'bad week' you'd want flagged — any specific metric thresholds?"

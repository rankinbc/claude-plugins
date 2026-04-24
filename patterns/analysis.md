# Shape: Data Analysis

Examine a dataset, extract insights, produce a report with charts.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/, project-level requirements.txt/pyproject.toml) lives at the project root.

## Default stack

- **Python 3.11+** + pandas + Jupyter OR a single script
- **matplotlib** or **plotly** for charts
- Output: markdown report + embedded/exported chart images

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                 # Purpose / inputs / outputs / how to run
└── analysis.py               # Or notebook.ipynb if user prefers notebooks
```

Input CSV/Excel/JSON files live in `data/<source_name>/` at the project root. Reports and chart PNGs land in `output/<component_name>/<YYYY-MM-DD>_<run>/` at the project root.

## Starter code

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (imports + a trivial "scaffolded stub" demo + a TODO marker). The code below is the implementation target `/execute-prp` uses during the build stage — matching the structure, patterns, and constraints shown.

**`analysis.py`**:

```python
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from pathlib import Path

COMPONENT_DIR = Path(__file__).parent
PROJECT_ROOT = COMPONENT_DIR.parent.parent
COMPONENT_NAME = COMPONENT_DIR.name

# Input and output paths — adjust <source_name> to match your data source
DATA_DIR = PROJECT_ROOT / "data" / "<source_name>"
RUN_DIR = PROJECT_ROOT / "output" / COMPONENT_NAME / f"{date.today().isoformat()}_run"
CHARTS_DIR = RUN_DIR / "charts"
RUN_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)

def load_data() -> pd.DataFrame:
    data_files = list(DATA_DIR.glob("*.csv"))
    if not data_files:
        raise FileNotFoundError(f"Drop a CSV file in {DATA_DIR} to begin")
    return pd.read_csv(data_files[0])

def profile(df: pd.DataFrame) -> dict:
    """Print and return summary stats — run this BEFORE analysis."""
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nDtypes:\n{df.dtypes}")
    print(f"\nMissing values:\n{df.isnull().sum()}")
    print(f"\nSample:\n{df.head()}")
    return {"rows": len(df), "nulls": df.isnull().sum().to_dict()}

def main():
    df = load_data()
    stats = profile(df)
    # TODO: actual analysis
    print(f"\nAnalysis complete. Report at: {RUN_DIR / 'report.md'}")

if __name__ == "__main__":
    main()
```

**Project-level `requirements.txt`** (at project root, shared across Python components):
```
pandas>=2.0
matplotlib>=3.8
# plotly>=5.18  # uncomment if using interactive charts
# openpyxl>=3.1  # uncomment if reading Excel files
```

## How to run

From the project root:

```bash
pip install -r requirements.txt
# Drop data file in data/<source_name>/
python components/<component_name>/analysis.py
# Report and charts appear in output/<component_name>/<date>_run/
```

## Gotchas for CLAUDE.md

- **Profile first, analyze second**: before any analysis, show me nulls, outliers, type issues, duplicates. Don't silently filter; announce what you dropped and why.
- **Executive summary at top**: the report starts with ONE paragraph any executive can read. Deep cuts come after.
- **One chart per key finding**: not a dashboard dump. Each chart justifies its existence with a caption tying it to a claim.
- **Don't over-model**: if the ask is descriptive ("what happened"), stay descriptive. Don't jump to regression/forecasting without asking.
- **Fiscal year ≠ calendar year** for many companies — confirm before doing "year-over-year" comparisons.
- **Unit/scale sanity checks**: if a number is an order of magnitude off from expectations, investigate before reporting.
- **Chart axis limits**: default matplotlib axes can mislead. Force zero-based Y when the story isn't "percent change."

## Validation

```bash
ruff check components/<component_name>/
python components/<component_name>/analysis.py
ls output/<component_name>/*/report.md >/dev/null && echo "Deliverable exists"
ls output/<component_name>/*/charts/*.png 2>/dev/null
```

## Project-level footprint

- `notebooks/` — exploratory hypothesis-testing notebooks outside the main analysis pipeline. Keep ad-hoc; promote anything durable into the component itself.

## Interview follow-ups

- "What data do you have? A spreadsheet, a database export, something from a tool?"
- "What question are you trying to answer? Be as specific as possible."
- "If you had to pick one finding to brief your boss on, what would it look like?"
- "Who's the audience — technical, executive, both?"
- "One-time analysis, or something you'll rerun as data updates?"

## INITIAL.md pre-fill

- **FEATURE**: The question(s) + what the deliverable answers
- **EXAMPLES**: Past analyses they liked, charts that worked well
- **DOCUMENTATION**: pandas groupby, matplotlib if needed
- **OTHER CONSIDERATIONS**: Data quirks (fiscal year, null conventions, unit confusion), audience, whether this will be re-run

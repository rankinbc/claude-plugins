# Shape: Dashboard

Interactive view of existing data. User wants to explore, filter, visualize.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/, the single `pyproject.toml`, and the single `.env`) lives at the project root.

## Default stack

- **Python 3.11+** (or user's Python if already installed)
- **Streamlit** — simplest path to an interactive UI without deployment hassle
- **pandas** — standard for data manipulation
- **plotly** or **matplotlib** — charts (Streamlit integrates cleanly with both; plotly for interactive hover, matplotlib for simpler static charts)

Fallback stacks if Streamlit isn't right:
- **FastAPI + Jinja + Chart.js** if they want a shareable web app (requires deployment thought)
- **Jupyter notebook** if they want a one-off exploration they'll check into git

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                 # Purpose / inputs / outputs / how to run (ce-scaffold writes it)
├── CLAUDE.md                 # Pattern gotchas, lazy-loaded (ce-scaffold writes it)
└── app.py                    # Streamlit entry point
```

Input data lives in `data/<source_name>/` at the project root. Dependencies live in the root `pyproject.toml` — never a component-local manifest. Secrets, if any, live in the root `.env`; name the keys in `## Gotchas for CLAUDE.md` and ce-scaffold reports them for the root `.env.example`.

## Starter code

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (imports + a trivial "scaffolded stub" demo + a TODO marker). The code below is the implementation target `/execute-prp` uses during the build stage — matching the structure, patterns, and constraints shown.

**`app.py`** (minimal runnable Streamlit):

```python
import streamlit as st
import pandas as pd
from pathlib import Path

COMPONENT_DIR = Path(__file__).parent
PROJECT_ROOT = COMPONENT_DIR.parent.parent
# Adjust <source_name> to match your data source
DATA_DIR = PROJECT_ROOT / "data" / "<source_name>"

st.set_page_config(page_title="<Component Title>", layout="wide")
st.title("<Component Title>")

@st.cache_data
def load_data():
    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        return None
    return pd.read_csv(csv_files[0])

df = load_data()

if df is None:
    st.warning(f"Drop a CSV file in `{DATA_DIR.relative_to(PROJECT_ROOT)}` to begin.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    # (filter widgets go here — customize based on columns)

col1, col2, col3 = st.columns(3)
col1.metric("Rows", len(df))
col2.metric("Columns", len(df.columns))

st.dataframe(df.head(20))
```

**Project-level `pyproject.toml`** (the single dependency manifest, shared across all components, with cache hygiene baked in):
```toml
[project]
dependencies = [
    "streamlit>=1.30",
    "pandas>=2.0",
    "plotly>=5.18",
]

[tool.pytest.ini_options]
testpaths = ["tests", "components"]
addopts = "-q --tb=short --no-header -ra --maxfail=3"   # keeps failing-gate output small
cache_dir = "~/.cache/pytest"

[tool.mypy]
cache_dir = "~/.cache/mypy"

[tool.ruff]
output-format = "concise"    # default "full" reprints source under every violation
cache-dir = "~/.cache/ruff"
```

## How to run

From the project root:

```bash
pip install -e .
streamlit run components/<component_name>/app.py
```

Opens at `http://localhost:8501`. That's it — no deployment needed.

## Gotchas for CLAUDE.md

- **Use `@st.cache_data` on data loading** — Streamlit reruns the whole script on every interaction. Uncached data reads will murder performance.
- **Filters must combine (AND, not OR)** — if the user picks "US region" + "Product X," show only Product X in US.
- **Empty states matter** — what if filters return zero rows? Show a friendly message, not a broken chart.
- **Charts should be readable at reasonable zoom** — avoid tiny labels, tiny fonts.
- **Don't over-customize** — Streamlit defaults are fine. No custom CSS unless the user explicitly asks.

## Validation

```bash
python -m ruff check components/<component_name>/
python -c "import streamlit, pandas; print('OK')"
streamlit run components/<component_name>/app.py --server.headless=true &
sleep 3 && curl -f http://localhost:8501 >/dev/null && echo "Dashboard loads"
kill %1
```

## INITIAL.md pre-fill hints

- **FEATURE**: Describe the KPIs / metrics / filters / views they want
- **EXAMPLES**: If they have sample data, reference it; otherwise note "data goes in `data/`"
- **DOCUMENTATION**: Link Streamlit docs (layouts, caching), pandas groupby docs
- **OTHER CONSIDERATIONS**: Timezones, fiscal year (!= calendar year for many companies), empty-state behavior, performance expectations (how big the data is)

## Questions to ask during interview (shape-specific follow-ups)

- "What's the data source — a spreadsheet, a database export, a CSV from somewhere?"
- "What are the 3-5 most important numbers you want to see at the top?"
- "Any filters people would want — by date, by region, by product, etc.?"
- "How will people access this — just you running locally, or shared with the team?"

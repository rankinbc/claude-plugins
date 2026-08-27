# Shape: Tracker

Simple list/status of items. Markdown files as source of truth; optional dashboard.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, .gitignore, shared data/ and output/, and the single `pyproject.toml`) lives at the project root.

## Default stack

- **Python 3.11+** + markdown files + optional Streamlit summary
- No database. Each tracked item = one markdown file. Anyone can open/edit in any editor.
- Summary script walks the markdown files and aggregates.

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                 # Purpose / inputs / outputs / how to run (ce-scaffold writes it)
├── CLAUDE.md                 # Pattern gotchas, lazy-loaded (ce-scaffold writes it)
├── items/                    # The tracked entities themselves — one markdown per item
│   └── .gitkeep
├── summary.py                # Reads markdown files → writes SUMMARY.md to output/
├── app.py                    # OPTIONAL: Streamlit dashboard for visual summary
└── config.yaml               # Status values, field definitions
```

The tracked-item markdown files live inside the component folder (they ARE the data — they're not "external inputs" living under `data/`). The summary output lands in the shared `output/<component_name>/<date>_<run>/` folder at the project root.

## Starter files

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (a skeleton template + a trivial runnable entry point + a TODO marker). The files below are the implementation target `/execute-prp` uses during the build stage — matching the structure, fields, and constraints shown.

**Per-item markdown template** (dropped in the tracked-entity folder):

```markdown
---
name:
start_date:
role:
manager:
status: pending
---

# {Name}

## Onboarding tasks
- [ ] Laptop setup
- [ ] Account access
- [ ] Training modules
- [ ] Intro meetings

## Notes

```

**`summary.py`** — walks the folder, parses frontmatter, writes SUMMARY.md to the project's `output/` folder:

```python
import yaml
from datetime import date
from pathlib import Path

COMPONENT_DIR = Path(__file__).parent
PROJECT_ROOT = COMPONENT_DIR.parent.parent
COMPONENT_NAME = COMPONENT_DIR.name

def parse_file(path: Path) -> dict:
    text = path.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1])

def main():
    items_dir = COMPONENT_DIR / "items"
    items = [parse_file(f) for f in items_dir.glob("*.md") if f.name != ".gitkeep"]

    summary = ["# Summary\n", f"Total: {len(items)}"]
    by_status = {}
    for i in items:
        by_status.setdefault(i.get("status", "unknown"), []).append(i)
    for status, batch in by_status.items():
        summary.append(f"\n## {status.title()} ({len(batch)})")
        for item in batch:
            summary.append(f"- {item.get('name', 'Unknown')}")

    out_dir = PROJECT_ROOT / "output" / COMPONENT_NAME / f"{date.today().isoformat()}_summary"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "SUMMARY.md").write_text("\n".join(summary))
    print(f"Summary written: {out_dir / 'SUMMARY.md'}")

if __name__ == "__main__":
    main()
```

**`config.yaml`**:
```yaml
# Status values the tracker accepts
allowed_statuses:
  - pending
  - in_progress
  - done
  - blocked

# Fields that every tracked item should have
required_fields:
  - name
  - start_date
```

## How to run

From the project root:

```bash
# Add items: create markdown files in components/<component_name>/items/
python components/<component_name>/summary.py
# Optional dashboard:
streamlit run components/<component_name>/app.py
```

Generated summaries land at `output/<component_name>/<YYYY-MM-DD>_summary/SUMMARY.md`.

## Gotchas for CLAUDE.md

- **Single source of truth**: the per-item markdown files ARE the data. Summary is derived. Never write back to the individual files from the summary script.
- **Human-editable, always**: anyone should be able to open a file, edit, save, and the summary picks it up. No hidden database, no state the user can't see.
- **Status values are a fixed set**: enforce `config.yaml`'s `allowed_statuses` when summarizing; flag unknowns loudly rather than silently treating as "other."
- **Privacy**: these files often contain personal data (dates, names, blockers). Default to gitignoring the per-item folder unless the user explicitly wants git history.
- **Keep it small**: max ~200 lines of Python total. A tracker should not become an application.

## Validation

```bash
ruff check components/<component_name>/
python components/<component_name>/summary.py
ls output/<component_name>/*/SUMMARY.md >/dev/null && echo "Summary generated"
```

## Interview follow-ups

- "What are you tracking — people, projects, tasks, something else?"
- "What are the key fields per item? (name, status, date, assignee, ...)"
- "What status values make sense? (pending/done is the simple default)"
- "Do you want a visual dashboard, or is a SUMMARY.md file enough?"
- "Should this be private (gitignored) or checked into git?"

# Shape: Form-and-View

Users enter data via a form. Data is stored. A summary view shows aggregate state.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/, project-level requirements.txt) lives at the project root.

## Default stack

- **Python 3.11+** + FastAPI + Jinja templates + SQLite
- Alternative: Streamlit if the UI is truly minimal (single page)

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                 # Purpose / inputs / outputs / how to run
├── app.py                    # FastAPI entry point
├── models.py                 # SQLAlchemy models
├── database.py               # DB setup + session
├── templates/
│   ├── base.html
│   ├── form.html             # Data entry
│   └── summary.html          # Aggregate view
└── static/
    └── style.css             # Minimal (Tailwind CDN in base.html works fine)
```

The SQLite database (`<component_name>.db`) lives under `data/<component_name>/` at the project root (it's the durable state, even if it's component-specific). Exported reports (CSV dumps, aggregated summaries) land in `output/<component_name>/<YYYY-MM-DD>_<run>/`.

## Starter code

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (imports + a trivial "scaffolded stub" demo + a TODO marker). The code below is the implementation target `/execute-prp` uses during the build stage — matching the structure, patterns, and constraints shown.

**`app.py`**:
```python
from fastapi import FastAPI, Form, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import Entry

Base.metadata.create_all(bind=engine)
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/submit")
def submit(name: str = Form(...), value: str = Form(...), db: Session = Depends(get_db)):
    db.add(Entry(name=name, value=value))
    db.commit()
    return RedirectResponse("/summary", status_code=303)

@app.get("/summary", response_class=HTMLResponse)
def summary(request: Request, db: Session = Depends(get_db)):
    entries = db.query(Entry).all()
    return templates.TemplateResponse("summary.html", {"request": request, "entries": entries})
```

**`models.py`**:
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class Entry(Base):
    __tablename__ = "entries"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

**`database.py`**:
```python
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

COMPONENT_DIR = Path(__file__).parent
PROJECT_ROOT = COMPONENT_DIR.parent.parent
COMPONENT_NAME = COMPONENT_DIR.name

DB_DIR = PROJECT_ROOT / "data" / COMPONENT_NAME
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / f"{COMPONENT_NAME}.db"

engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## How to run

From the project root:

```bash
pip install -r requirements.txt
uvicorn components.<component_name>.app:app --reload
# Open http://localhost:8000
```

## Gotchas for CLAUDE.md

- **Auth is usually out of scope** for internal tools on a trusted network. If the user explicitly needs logins, escalate to a real auth story.
- **SQLite is fine** until it isn't. Fine for single-node internal tools with <50 concurrent users. Migrate to Postgres if that changes.
- **No delete by default**: the source of truth is the DB; don't let people destroy history casually. Add soft-delete (`is_deleted` column) before hard-delete.
- **Form validation at two layers**: HTML `required`/`type` attributes AND server-side Pydantic/SQLAlchemy constraints. Client-side is convenience; server-side is trust.
- **CSRF**: FastAPI doesn't ship CSRF out of the box for form POSTs. If the app is anything but a trusted-LAN internal tool, add `fastapi-csrf-protect` or equivalent.
- **Seed data**: include 2-3 example entries so the `/summary` page isn't empty on first view.

## Validation

```bash
ruff check components/<component_name>/
python -c "from components.<component_name>.app import app; print('import ok')"
uvicorn components.<component_name>.app:app --host 127.0.0.1 --port 8765 &
sleep 2 && curl -f http://127.0.0.1:8765/ >/dev/null && echo "OK"
kill %1
```

## Interview follow-ups

- "What data gets entered? (fields, types)"
- "Who submits vs. who just views? Is there a role distinction?"
- "What should the summary show — everyone's submissions, filtered, aggregated?"
- "How many submissions do you expect per day?"
- "Does this need to be shareable on your network, or is localhost fine?"
- "Do you need export (CSV download)?"

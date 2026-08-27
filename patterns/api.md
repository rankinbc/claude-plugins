# Shape: REST API

CRUD API with users, auth, persistence, tests. Real software.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/, the single `pyproject.toml`, and the single `.env`) lives at the project root. Even when the API is the only component, its dependencies and secrets belong to the project root, not the component folder.

## Default stack

- **Python 3.11+** + FastAPI + SQLAlchemy 2.0 + PostgreSQL (SQLite for dev)
- **Alembic** for migrations from day one
- **pytest** + httpx for testing
- **passlib** + **python-jose** for auth (bcrypt passwords, JWT tokens)

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                 # Purpose / inputs / outputs / how to run (ce-scaffold writes it)
├── CLAUDE.md                 # Pattern gotchas, lazy-loaded (ce-scaffold writes it)
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI instance + router includes
│   ├── config.py             # Pydantic-settings
│   ├── database.py
│   ├── deps.py               # Dependency injection
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic DTOs
│   ├── routes/               # Endpoint modules
│   ├── services/             # Business logic
│   └── security.py           # JWT + password hashing
├── alembic/
│   ├── versions/
│   └── env.py
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_*.py
└── alembic.ini
```

For dev, the SQLite DB file lives under `data/<component_name>/` at the project root. Prod uses PostgreSQL configured via `DATABASE_URL` in the **project-root** `.env` — there is no component-local `.env`, and `app/config.py` loads `PROJECT_ROOT / ".env"`. Exported data (CSV dumps, backup snapshots) lands in `output/<component_name>/<YYYY-MM-DD>_<run>/`.

## Starter code

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (imports + a trivial "scaffolded stub" demo + a TODO marker). The code below is the implementation target `/execute-prp` uses during the build stage — matching the structure, patterns, and constraints shown.

**`app/main.py`**:
```python
from fastapi import FastAPI
from app.routes import auth
from app.database import engine, Base

# Base.metadata.create_all(bind=engine)  # Dev only — use Alembic in prod

app = FastAPI(title="<Project Name>")
app.include_router(auth.router, prefix="/auth", tags=["auth"])
```

**`app/database.py`**:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
```

**`tests/conftest.py`** (pytest fixtures for isolated DB per test):
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    yield TestingSession

@pytest.fixture
def client(test_db):
    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

## Gotchas for CLAUDE.md

- **Authorization at the query level**: never fetch then check. Always `WHERE owner_id = current_user.id` in the query. Prevents IDOR bugs.
- **Alembic migrations from day one**: no `Base.metadata.create_all()` in prod paths. First commit includes Alembic setup.
- **JWT expiry**: 24h default for access tokens. No refresh token in v1 (add when needed).
- **Password rules**: min 10 chars, bcrypt default work factor. No max length unless a DB column forces it.
- **Error shape**: `{"detail": "message"}` via FastAPI HTTPException. Never expose ORM errors or stack traces to clients.
- **Pagination**: every list endpoint paginates from the start (`?limit=50&offset=0`). Max limit 200.
- **Testing matrix**: every endpoint gets (1) success, (2) unauthorized (no token), (3) forbidden (other user's resource).
- **Pydantic v2**: use v2 idioms (`model_config`, not `Config` class). Upstream moved.
- **SQLAlchemy 2.0**: use new-style `select()` + `session.execute()`, not legacy `session.query()`.
- **Secrets** (`DATABASE_URL`, `JWT_SECRET_KEY`) come from the project-root `.env` only — `app/config.py` points pydantic-settings at `PROJECT_ROOT / ".env"`. Never a component-local `.env`, never a default value baked into `config.py`.

## Validation

From the project root:

```bash
ruff check components/<component_name>/
mypy components/<component_name>/app/
pytest -q components/<component_name>/tests/
# Startup smoke:
(cd components/<component_name> && uvicorn app.main:app --host 127.0.0.1 --port 8765 &)
sleep 2 && curl -f http://127.0.0.1:8765/docs >/dev/null && echo "OK"
kill %1
```

## Project-level footprint

- `migrations/` — DB schema migrations (Alembic or equivalent). Migrations are a project-level artifact — schema evolution affects every component that touches the DB, not just the API component that first created it.
- `schemas/` — shared OpenAPI or JSON schema files when the API's types are consumed by other components (e.g., a frontend, a CLI, another service).

## Interview follow-ups

- "What resources does the API expose? (users? posts? products? tasks?)"
- "Do users have accounts with passwords, or is it API-key-only?"
- "Multi-tenant (each user sees only their own stuff) or shared data?"
- "Will this be consumed by a frontend you're also building, or just a standalone API?"
- "Production target — cloud (AWS/GCP), self-hosted, local only for now?"
- "Any integrations required from day one (payment, email, external APIs)?"

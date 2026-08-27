# Shape: System Integration

Sync data between two systems. Handle rate limits, retries, resumability, error recovery.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/, the single `pyproject.toml`, and the single `.env`) lives at the project root.

## Default stack

- **Python 3.11+** + **httpx** or **requests** + **SQLAlchemy** (for state persistence)
- PostgreSQL for the local store (SQLite for small-scale)
- Daemon mode via **apscheduler** or simple loop; one-shot mode for cron use

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                   # Purpose / inputs / outputs / how to run (ce-scaffold writes it)
├── CLAUDE.md                   # Pattern gotchas, lazy-loaded (ce-scaffold writes it)
├── src/
│   └── <package>/
│       ├── __init__.py
│       ├── client.py           # External API wrapper (rate-limit-aware)
│       ├── sync.py             # Sync engine
│       ├── models.py           # Local DB models
│       ├── state.py            # Last-sync tracking
│       └── cli.py              # run / sync-once / backfill commands
├── alembic/
├── tests/
└── Dockerfile                  # For deployment (if this component deploys standalone)
```

Dependencies go in the root `pyproject.toml`; secrets go in the root `.env`. Name the keys this component needs in `## Gotchas for CLAUDE.md` — ce-scaffold reports them and the main session writes the root `.env.example`.

The local sync database (SQLite for small-scale, or a pointer to an external Postgres for larger) lives under `data/<component_name>/` at the project root. Per-run logs and failed-item dumps for manual review land in `output/<component_name>/<YYYY-MM-DD>_<run>/`.

## Starter code

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (imports + a trivial "scaffolded stub" demo + a TODO marker). The code below is the implementation target `/execute-prp` uses during the build stage — matching the structure, patterns, and constraints shown.

**`src/<package>/client.py`** (rate-limit-aware HTTP client):
```python
import logging
import time
import httpx
from typing import Any

log = logging.getLogger(__name__)

class RateLimitedClient:
    def __init__(self, base_url: str, token: str):
        self.client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    def get(self, path: str, **params) -> dict[str, Any]:
        for attempt in range(5):
            resp = self.client.get(path, params=params)
            remaining = int(resp.headers.get("X-RateLimit-Remaining", "1000"))
            reset = int(resp.headers.get("X-RateLimit-Reset", "0"))

            if resp.status_code == 429:
                wait = max(reset - time.time(), 60)
                log.warning("Rate limited; sleeping %.0fs", wait)
                time.sleep(wait)
                continue

            resp.raise_for_status()
            if remaining < 100:
                log.info("Rate limit low (%d remaining); pausing", remaining)
                time.sleep(5)
            return resp.json()
        raise RuntimeError("Retries exhausted")
```

**`src/<package>/sync.py`** (upsert pattern):
```python
from sqlalchemy.dialects.postgresql import insert
from .models import Issue

def upsert_issue(db, issue_data: dict):
    stmt = insert(Issue).values(**issue_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["github_id"],
        set_={
            "title": stmt.excluded.title,
            "state": stmt.excluded.state,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    db.execute(stmt)
    db.commit()
```

## Gotchas for CLAUDE.md

- **Idempotency is critical**: `INSERT ... ON CONFLICT UPDATE` (upsert). Running twice must be safe.
- **Never delete**: if a record vanishes from the external API, mark `deleted_at`; don't actually DELETE.
- **Rate-limit discipline**: stop polling when remaining < 100. Wait for reset.
- **Pagination**: follow Link headers; don't assume page sizes.
- **Transactions per entity**: each unit's sync is a transaction. Partial failure rolls back that unit, other units continue.
- **Observability**: log structured JSON per cycle (started_at, repo, fetched, inserted, updated, duration_ms, errors).
- **Graceful SIGTERM**: finish the current unit, exit cleanly. Don't leave half-synced state.
- **Secrets only in the project-root `.env`**, loaded via `load_dotenv(PROJECT_ROOT / ".env")`. No tokens in `config.yaml`, no tokens in code, no component-local `.env`.
- **Backfill command**: separate entry point for re-syncing one entity from scratch.

## Validation

From the project root:

```bash
ruff check components/<component_name>/src/
pytest -q components/<component_name>/tests/
# With mocked API responses (use `responses` lib in tests):
pytest components/<component_name>/tests/test_rate_limit.py
```

## Project-level footprint

- `mappings/` — field-mapping tables between source and destination systems (YAML/JSON/CSV). Keeping these at the project root makes them version-controlled review artifacts and reusable if a second integration needs the same mapping.

## Interview follow-ups

- "What two systems are you syncing? (A is source-of-truth, B is the replica?)"
- "How often does it need to sync — real-time, every few minutes, daily?"
- "What fields matter? Full record copy, or a subset?"
- "What happens when records are deleted in the source?"
- "Who owns authentication — OAuth, API key, both?"
- "Where does this run — a server, Kubernetes, cron on a laptop?"

# Shape: Automation

Runs on a trigger (schedule, event, webhook), does work, notifies. No UI beyond logs and alerts.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, shared data/ and output/, the single `pyproject.toml`, and the single `.env`) lives at the project root.

## Default stack

- **Python 3.11+**
- **cron** (Linux/Mac) or Task Scheduler (Windows) for scheduling
- **python-dotenv** for config, **logging** stdlib, **requests** or **httpx** for API calls
- Notification via Slack webhook / email / SMS depending on the user's need

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md              # Purpose / inputs / outputs / how to run (ce-scaffold writes it)
├── CLAUDE.md              # Pattern gotchas, lazy-loaded (ce-scaffold writes it)
├── main.py                # Entry point; accepts --dry-run
├── config.yaml            # Non-secret config (rules, thresholds, channels)
└── crontab.example        # Example cron line
```

Secrets come from the **project-root** `.env` — this component has none of its own. Name the keys it needs in `## Gotchas for CLAUDE.md`; ce-scaffold reports them and the main session writes the root `.env.example`.

Processed-record state and logs live under `output/<component_name>/` at the project root:
- `output/<component_name>/state/processed.json` — durable idempotency state (kept across runs, not per-run)
- `output/<component_name>/<YYYY-MM-DD>_run/run.log` — that run's log, alongside anything else the run produced

External inputs (if the automation consumes files rather than APIs) live in `data/<source_name>/` at the project root.

## Starter code

> **Reference idiom for `/execute-prp`**, not what ce-scaffold ships. The scaffolder writes minimum-viable stubs (imports + a trivial "scaffolded stub" demo + a TODO marker). The code below is the implementation target `/execute-prp` uses during the build stage — matching the structure, patterns, and constraints shown.

**`main.py`** (idempotency + dry-run pattern):
```python
import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

COMPONENT_DIR = Path(__file__).parent
PROJECT_ROOT = COMPONENT_DIR.parent.parent
COMPONENT_NAME = COMPONENT_DIR.name

load_dotenv(PROJECT_ROOT / ".env")   # one .env for the whole project

OUTPUT_DIR = PROJECT_ROOT / "output" / COMPONENT_NAME
STATE_FILE = OUTPUT_DIR / "state" / "processed.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
RUN_DIR = OUTPUT_DIR / f"{today}_run"    # this run's artifacts, log included
RUN_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(RUN_DIR / "run.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()

def save_state(ids: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(ids)))

def fetch_items() -> list[dict]:
    # TODO: real fetch
    return []

def process(item: dict) -> None:
    # TODO: real work
    log.info("processed %s", item["id"])

def notify(summary: str) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        log.warning("No SLACK_WEBHOOK_URL set; skipping notification")
        return
    # TODO: post to Slack

def main(dry_run: bool) -> None:
    processed = load_state()
    items = fetch_items()
    new = [i for i in items if i["id"] not in processed]

    log.info("found %d new items (%d already processed)", len(new), len(processed))

    if dry_run:
        log.info("[dry-run] would process: %s", [i["id"] for i in new])
        return

    for item in new:
        try:
            process(item)
            processed.add(item["id"])
        except Exception:
            log.exception("failed to process %s", item["id"])

    save_state(processed)
    notify(f"Processed {len(new)} items. Total ever: {len(processed)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
```

**`crontab.example`**:
```
# Every day at 6 AM UTC
0 6 * * * cd /path/to/project && /path/to/venv/bin/python components/<component_name>/main.py >> output/<component_name>/cron.log 2>&1
```

**Secret keys this component declares** — reported to the main session, which writes them into the project-root `.env.example`. Never write a component-local `.env.example`:
```
SLACK_WEBHOOK_URL    # Slack app > Incoming Webhooks
API_KEY              # the upstream service this automation talks to
DATABASE_URL         # only if the automation persists to a DB
```

## How to run

From the project root:

```bash
pip install -e .
.\scripts\secure\Set-ProjectSecrets.ps1                # fills the project-root .env; run it yourself, not through Claude
python components/<component_name>/main.py --dry-run   # Preview what would happen
python components/<component_name>/main.py             # Actual run
```

## Gotchas for CLAUDE.md

- **Idempotency is non-negotiable**: if the script runs twice (retry, manual re-run), it must NOT cause duplicates. Track processed IDs in state/processed.json or equivalent.
- **Dry-run mode always**: `--dry-run` must fetch + classify + print what would happen, without taking real action. Essential for testing changes safely.
- **Secrets only in the project-root `.env`**, loaded via `load_dotenv(PROJECT_ROOT / ".env")`. Never in code, never in `config.yaml`, never a component-local `.env`. `config.yaml` holds non-secret knobs only.
- **Logs are run artifacts**: each run writes `output/<component_name>/<YYYY-MM-DD>_run/run.log` alongside that run's other output. Never a top-level `logs/` folder. Durable state (`state/processed.json`) is the one thing that lives outside a dated run folder.
- **Log files rotate**: keep the latest ~5 run folders directly under `output/<component_name>/`, move older ones to `_archive/`.
- **Timezone = UTC** in logs and schedule. Any user-facing timestamp can be converted; internal state stays UTC.
- **Failures are non-fatal per item**: one bad record shouldn't crash the whole run. Log the exception, continue to the next.
- **Alerting on failure**: if the entire run fails (not per-item), send an alert to a different channel so it doesn't get lost in routine logs.

## Validation

```bash
python -m ruff check components/<component_name>/
python components/<component_name>/main.py --dry-run
test -d output/<component_name>/state
ls -d output/<component_name>/*_run/run.log
grep -q "0 6" components/<component_name>/crontab.example
```

## Interview follow-ups

- "What triggers this — a clock/schedule, an event, an incoming webhook?"
- "What does it do when it runs? Walk me through the steps."
- "What's the output? A file, a notification, a row in a database?"
- "Where should notifications go — Slack, email, something else?"
- "What counts as failure? Any items that can't be processed, or only if the whole thing breaks?"
- "How do you want to know about failures — same notification channel, or separate?"

"""Lightweight JSONL event logging.

We log:
- the generated plan (SQL/binds/classification + policy outcome)
- the execution attempt result (success/failure)

We intentionally do NOT log:
- environment variables (which may contain secrets)
- Oracle passwords
- OpenAI API keys

Logs go to:
- `.nl_dba_executor_logs/events-YYYY-MM-DD.jsonl`
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict


def now_iso_utc() -> str:
    """Return current UTC timestamp in ISO-8601 `...Z` form."""
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def log_dir() -> Path:
    """Return (and create) the directory where JSONL logs are stored."""
    p = Path(".nl_dba_executor_logs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_event(event: Dict[str, Any]) -> None:
    """Append a single JSON object as a JSONL line to today's log file."""
    # Avoid leaking secrets: do not log env vars or passwords.
    log_path = log_dir() / f"events-{_dt.date.today().isoformat()}.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

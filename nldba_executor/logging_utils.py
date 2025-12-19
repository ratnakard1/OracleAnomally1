from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict


def now_iso_utc() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def log_dir() -> Path:
    p = Path(".nl_dba_executor_logs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_event(event: Dict[str, Any]) -> None:
    # Avoid leaking secrets: do not log env vars or passwords.
    log_path = log_dir() / f"events-{_dt.date.today().isoformat()}.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

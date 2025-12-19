from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple


def _oracle_connect():
    try:
        import oracledb  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency 'oracledb'. Install with: pip install -r requirements.txt"
        ) from e

    user = os.environ.get("ORACLE_USER")
    password = os.environ.get("ORACLE_PASSWORD")
    dsn = os.environ.get("ORACLE_DSN")

    missing = [
        k
        for k, v in [("ORACLE_USER", user), ("ORACLE_PASSWORD", password), ("ORACLE_DSN", dsn)]
        if not v
    ]
    if missing:
        raise RuntimeError(f"Missing Oracle env vars: {', '.join(missing)}")

    return oracledb.connect(user=user, password=password, dsn=dsn)


def _format_rows(columns: List[str], rows: List[Tuple[Any, ...]]) -> str:
    # Simple table renderer.
    srows = [["" if v is None else str(v) for v in r] for r in rows]
    widths = [len(c) for c in columns]
    for r in srows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(r: List[str]) -> str:
        return " | ".join(r[i].ljust(widths[i]) for i in range(len(columns)))

    out: List[str] = []
    out.append(fmt_row(columns))
    out.append("-+-".join("-" * w for w in widths))
    for r in srows:
        out.append(fmt_row(r))
    return "\n".join(out)


def execute_oracle_sql(sql: str, binds: Dict[str, Any], fetch: int) -> Tuple[str, Optional[str]]:
    conn = _oracle_connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, binds or None)

        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(fetch)
            return _format_rows(cols, rows), None

        # Non-query: commit.
        conn.commit()
        return "OK (statement executed and committed)", None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return "", str(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass

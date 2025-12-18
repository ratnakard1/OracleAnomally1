"""Natural-language DBA command executor for Oracle.

Goal: take a human request, generate Oracle SQL safely, and (optionally) execute.

Safety model:
- We ALWAYS run a local policy check on model output.
- By default we do NOT execute; use --execute.
- Destructive commands are blocked unless explicitly allowed via env.

Env vars:
- OPENAI_API_KEY (required)
- OPENAI_MODEL (optional; default: gpt-4o-mini)

Oracle connection (required only with --execute):
- ORACLE_USER
- ORACLE_PASSWORD
- ORACLE_DSN (e.g. "host:1521/service" or TNS name)

Optional safety toggles:
- NLDBA_READONLY=1            (force SELECT-only)
- NLDBA_ALLOW_DESTRUCTIVE=1   (allow DROP/TRUNCATE/SHUTDOWN etc; still requires confirmation)

Usage:
- python nl_dba_executor.py "show blocking sessions"          (dry-run)
- python nl_dba_executor.py "kill session sid 123 serial 456" --execute
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -------------------------
# Models / types
# -------------------------


@dataclass(frozen=True)
class Plan:
    request: str
    classification: str
    sql: str
    binds: Dict[str, Any]
    explanation: str
    risks: List[str]
    requires_confirmation: bool


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_confirmation: bool
    reason: str
    red_flags: List[str]


# -------------------------
# Utilities
# -------------------------


def _now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _log_dir() -> Path:
    p = Path(".nl_dba_executor_logs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_log(event: Dict[str, Any]) -> None:
    # Avoid leaking secrets: do not log env vars or passwords.
    log_path = _log_dir() / f"events-{_dt.date.today().isoformat()}.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _print_kv(title: str, kv: List[Tuple[str, str]]) -> None:
    print(title)
    for k, v in kv:
        print(f"- {k}: {v}")


def _prompt_confirm(prompt: str) -> bool:
    ans = input(prompt).strip().lower()
    return ans in {"y", "yes"}


# -------------------------
# OpenAI: NL -> SQL plan
# -------------------------


_SYSTEM_PROMPT = """You are an expert Oracle Database DBA assistant.

Task: Convert the user's natural-language DBA request into a single Oracle SQL statement (or an anonymous PL/SQL block if needed).

Rules:
- Output MUST be valid JSON only (no markdown, no commentary).
- JSON schema:
  {
    "classification": "read_only" | "dml" | "ddl" | "admin" | "unknown",
    "sql": "...",
    "binds": {"name": value, ...},
    "explanation": "...",
    "risks": ["...", ...],
    "requires_confirmation": true|false
  }
- Prefer querying Oracle dynamic performance views (v$*) where appropriate.
- For potentially destructive operations (kill session, DDL, DML, ALTER SYSTEM, user/privilege changes), set requires_confirmation=true and include risks.
- Never invent schema objects. If a request depends on unknown schema/table names, produce a safe inspection query instead.
- Do not include credentials.
"""


def _openai_client():
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency 'openai'. Install with: pip install -r requirements.txt"
        ) from e
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def generate_plan(request: str, model: str) -> Plan:
    client = _openai_client()

    # Prefer JSON mode when available to reduce invalid JSON responses.
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": request},
            ],
        )
    except TypeError:
        # Older client/model that doesn't support response_format.
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": request},
            ],
        )

    content = (resp.choices[0].message.content or "").strip()
    try:
        obj = json.loads(content)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            "Model did not return valid JSON. "
            "Re-run with a simpler request or set OPENAI_MODEL to a different model.\n\n"
            f"Raw output:\n{content}"
        ) from e

    def _get_str(key: str) -> str:
        v = obj.get(key)
        return v if isinstance(v, str) else ""

    classification = _get_str("classification") or "unknown"
    sql = _get_str("sql")
    binds = obj.get("binds")
    explanation = _get_str("explanation")
    risks = obj.get("risks")
    requires_confirmation = obj.get("requires_confirmation")

    if not isinstance(binds, dict):
        binds = {}
    if not isinstance(risks, list) or not all(isinstance(x, str) for x in risks):
        risks = []
    if not isinstance(requires_confirmation, bool):
        requires_confirmation = False

    if not sql.strip():
        classification = "unknown"
        sql = "SELECT 'Unable to produce SQL for request' AS message FROM dual"
        requires_confirmation = False

    return Plan(
        request=request,
        classification=classification,
        sql=sql.strip().rstrip(";"),
        binds=binds,
        explanation=explanation.strip(),
        risks=risks,
        requires_confirmation=requires_confirmation,
    )


# -------------------------
# Safety policy
# -------------------------


_FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
    (r"\bdrop\b", "DROP statements are destructive"),
    (r"\btruncate\b", "TRUNCATE is destructive"),
    (r"\bshutdown\b", "SHUTDOWN affects database availability"),
    (r"\bstartup\b", "STARTUP affects database availability"),
    (r"\balter\s+system\b", "ALTER SYSTEM is high-risk"),
    (r"\bcreate\s+user\b", "User creation changes security posture"),
    (r"\balter\s+user\b", "User alteration changes security posture"),
    (r"\bgrant\b", "GRANT changes privileges"),
    (r"\brevoke\b", "REVOKE changes privileges"),
]

_CONFIRM_PATTERNS: List[Tuple[str, str]] = [
    (r"\bdelete\b", "DELETE modifies data"),
    (r"\bupdate\b", "UPDATE modifies data"),
    (r"\binsert\b", "INSERT modifies data"),
    (r"\bmerge\b", "MERGE modifies data"),
    (r"\bcreate\b", "CREATE changes schema"),
    (r"\balter\b", "ALTER changes schema/system"),
    (r"\bcomment\s+on\b", "COMMENT modifies metadata"),
    (r"\bkill\s+session\b", "Killing sessions can disrupt users/transactions"),
]


def _normalize_sql_for_policy(sql: str) -> str:
    # Remove string literals to reduce false positives (very light-weight).
    sql2 = re.sub(r"'(?:''|[^'])*'", "'…'", sql)
    # Collapse whitespace, lowercase.
    sql2 = re.sub(r"\s+", " ", sql2).strip().lower()
    return sql2


def policy_check(plan: Plan, readonly: bool, allow_destructive: bool) -> PolicyDecision:
    sqln = _normalize_sql_for_policy(plan.sql)

    red_flags: List[str] = []
    forbidden_hits: List[str] = []
    confirm_hits: List[str] = []

    for pat, reason in _FORBIDDEN_PATTERNS:
        if re.search(pat, sqln):
            forbidden_hits.append(reason)

    for pat, reason in _CONFIRM_PATTERNS:
        if re.search(pat, sqln):
            confirm_hits.append(reason)

    # Basic read-only enforcement.
    if readonly:
        # Allow common safe read-only statements (SELECT/WITH) and EXPLAIN PLAN.
        if not re.match(r"^(select|with|explain)\b", sqln):
            return PolicyDecision(
                allowed=False,
                requires_confirmation=False,
                reason="Readonly mode is enabled; only SELECT/WITH/EXPLAIN are allowed.",
                red_flags=["readonly_mode_violation"],
            )

    if forbidden_hits and not allow_destructive:
        return PolicyDecision(
            allowed=False,
            requires_confirmation=False,
            reason=(
                "Blocked by safety policy (set NLDBA_ALLOW_DESTRUCTIVE=1 to override). "
                + "; ".join(sorted(set(forbidden_hits)))
            ),
            red_flags=["forbidden:" + x for x in sorted(set(forbidden_hits))],
        )

    requires_confirmation = plan.requires_confirmation or bool(confirm_hits) or bool(forbidden_hits)

    if forbidden_hits and allow_destructive:
        red_flags.extend(["destructive_allowed_env"])  # still confirm

    red_flags.extend(["confirm:" + x for x in sorted(set(confirm_hits))])

    return PolicyDecision(
        allowed=True,
        requires_confirmation=requires_confirmation,
        reason="Allowed by safety policy.",
        red_flags=red_flags,
    )


# -------------------------
# Oracle execution
# -------------------------


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

    missing = [k for k, v in [("ORACLE_USER", user), ("ORACLE_PASSWORD", password), ("ORACLE_DSN", dsn)] if not v]
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

    out = []
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


# -------------------------
# CLI
# -------------------------


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Natural-language DBA command executor (Oracle + OpenAI)")
    ap.add_argument("request", help="Natural language request, e.g. 'show tablespace usage'")
    ap.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), help="OpenAI model")
    ap.add_argument("--execute", action="store_true", help="Actually run against Oracle (default: dry-run)")
    ap.add_argument("--fetch", type=int, default=50, help="Max rows to fetch for SELECT")
    ap.add_argument("--no-confirm", action="store_true", help="Do not prompt; fail if confirmation required")

    args = ap.parse_args(argv)

    if not os.environ.get("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY env var", file=sys.stderr)
        return 2

    readonly = os.environ.get("NLDBA_READONLY", "0") == "1"
    allow_destructive = os.environ.get("NLDBA_ALLOW_DESTRUCTIVE", "0") == "1"

    plan = generate_plan(args.request, model=args.model)
    decision = policy_check(plan, readonly=readonly, allow_destructive=allow_destructive)

    _write_log(
        {
            "ts": _now_iso(),
            "event": "plan_generated",
            "request": plan.request,
            "classification": plan.classification,
            "sql": plan.sql,
            "binds": plan.binds,
            "policy_allowed": decision.allowed,
            "policy_requires_confirmation": decision.requires_confirmation,
            "policy_reason": decision.reason,
            "policy_red_flags": decision.red_flags,
        }
    )

    _print_kv(
        "Plan",
        [
            ("classification", plan.classification),
            ("requires_confirmation", str(plan.requires_confirmation)),
            ("policy_allowed", str(decision.allowed)),
            ("policy_requires_confirmation", str(decision.requires_confirmation)),
        ],
    )
    print("\nSQL")
    print(plan.sql)
    if plan.binds:
        print("\nBinds")
        print(json.dumps(plan.binds, indent=2, ensure_ascii=False))
    if plan.explanation:
        print("\nExplanation")
        print(plan.explanation)
    if plan.risks:
        print("\nRisks")
        for r in plan.risks:
            print(f"- {r}")

    if not decision.allowed:
        print(f"\nBLOCKED: {decision.reason}", file=sys.stderr)
        return 3

    if not args.execute:
        print("\nDry-run only (use --execute to run against Oracle).")
        return 0

    if decision.requires_confirmation:
        if args.no_confirm:
            print("\nConfirmation required but --no-confirm was set.", file=sys.stderr)
            return 4
        if not _prompt_confirm("\nThis action is high-risk. Type 'yes' to proceed [y/N]: "):
            print("Cancelled.")
            return 0

    output, err = execute_oracle_sql(plan.sql, plan.binds, fetch=max(1, args.fetch))

    _write_log(
        {
            "ts": _now_iso(),
            "event": "execution_attempt",
            "request": plan.request,
            "sql": plan.sql,
            "binds": plan.binds,
            "ok": err is None,
            "error": err,
        }
    )

    if err:
        print(f"\nERROR: {err}", file=sys.stderr)
        return 5

    print("\nResult")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

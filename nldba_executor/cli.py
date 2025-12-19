"""Command-line interface entrypoint.

Flow:
1) Parse args + read env
2) Use OpenAI to generate a structured `Plan`
3) Run local `policy_check` on the SQL
4) Print the plan
5) If --execute, optionally require user confirmation and execute against Oracle

Required env:
- OPENAI_API_KEY

Oracle env (required only with --execute):
- ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN

Safety env:
- NLDBA_READONLY=1
- NLDBA_ALLOW_DESTRUCTIVE=1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from .console import print_kv, prompt_confirm
from .logging_utils import now_iso_utc, write_event
from .openai_plan import generate_plan
from .oracle_exec import execute_oracle_sql
from .policy import policy_check


def main(argv: Optional[List[str]] = None) -> int:
    """CLI main function. Returns a process exit code."""
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

    write_event(
        {
            "ts": now_iso_utc(),
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

    print_kv(
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
        if not prompt_confirm("\nThis action is high-risk. Type 'yes' (or 'y') to proceed [y/yes/N]: "):
            print("Cancelled.")
            return 0

    output, err = execute_oracle_sql(plan.sql, plan.binds, fetch=max(1, args.fetch))

    write_event(
        {
            "ts": now_iso_utc(),
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

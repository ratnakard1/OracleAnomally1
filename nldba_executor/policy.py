"""Local safety policy for generated SQL.

This is the critical defense-in-depth layer:
- Even if the model generates unsafe SQL, we scan and block/confirm locally.

Policy knobs are controlled by the CLI via env vars:
- NLDBA_READONLY=1
  - Only allow SQL that starts with SELECT/WITH/EXPLAIN
- NLDBA_ALLOW_DESTRUCTIVE=1
  - Allow high-risk keywords like DROP/TRUNCATE/SHUTDOWN (but still confirm)
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .types import Plan, PolicyDecision


FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
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

CONFIRM_PATTERNS: List[Tuple[str, str]] = [
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
    """Normalize SQL for pattern scanning.

    We do a *very* light normalization:
    - replace string literals with a placeholder (reduce false positives)
    - lowercase and collapse whitespace
    """
    # Remove string literals to reduce false positives (very light-weight).
    sql2 = re.sub(r"'(?:''|[^'])*'", "'…'", sql)
    # Collapse whitespace, lowercase.
    sql2 = re.sub(r"\s+", " ", sql2).strip().lower()
    return sql2


def policy_check(plan: Plan, readonly: bool, allow_destructive: bool) -> PolicyDecision:
    """Decide whether a plan is allowed to run and whether it needs confirmation.

    Returns:
    - PolicyDecision.allowed=False if blocked (e.g. readonly violation, destructive blocked)
    - PolicyDecision.requires_confirmation=True if risky patterns are present
      or if the model already flagged it as risky via Plan.requires_confirmation
    """
    sqln = _normalize_sql_for_policy(plan.sql)

    red_flags: List[str] = []
    forbidden_hits: List[str] = []
    confirm_hits: List[str] = []

    for pat, reason in FORBIDDEN_PATTERNS:
        if re.search(pat, sqln):
            forbidden_hits.append(reason)

    for pat, reason in CONFIRM_PATTERNS:
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

"""Shared datatypes used across the executor.

Why this module exists:
- Keeps the data contracts (`Plan`, `PolicyDecision`) in one place so the CLI,
  policy checks, model output parsing, and Oracle execution stay loosely coupled.

These classes are intentionally small and JSON-friendly:
- `Plan` mirrors what the LLM is instructed to return.
- `PolicyDecision` is the *local* verdict after scanning `Plan.sql`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class Plan:
    """Model-produced execution plan.

    Fields:
    - request: The original natural language prompt from the user.
    - classification: One of the model's coarse labels (read_only/dml/ddl/admin/unknown).
    - sql: Oracle SQL statement (or anonymous PL/SQL block) with no trailing semicolon.
    - binds: Bind variables to pass to the driver (named binds), e.g. {"sid": 123}.
    - explanation: Short explanation of what the SQL does.
    - risks: Human-readable risks associated with running the SQL.
    - requires_confirmation: Model hint that this is high-risk and should be confirmed.
    """

    request: str
    classification: str
    sql: str
    binds: Dict[str, Any]
    explanation: str
    risks: List[str]
    requires_confirmation: bool


@dataclass(frozen=True)
class PolicyDecision:
    """Local safety-policy decision for a given `Plan`.

    Notes:
    - The model can *suggest* confirmation via `Plan.requires_confirmation`, but
      the final decision is made locally by scanning SQL for risky patterns and
      enforcing optional read-only mode.
    """

    allowed: bool
    requires_confirmation: bool
    reason: str
    red_flags: List[str]

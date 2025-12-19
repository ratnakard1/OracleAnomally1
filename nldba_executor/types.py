from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


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

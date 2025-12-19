"""OpenAI integration: natural language -> structured Oracle SQL plan.

This module is responsible ONLY for:
- calling the OpenAI API
- requesting a strict JSON object
- validating/parsing that JSON into a `Plan`

It is NOT responsible for:
- enforcing safety rules (see `nldba_executor/policy.py`)
- executing SQL (see `nldba_executor/oracle_exec.py`)

Required env:
- OPENAI_API_KEY

Optional env:
- OPENAI_MODEL (the CLI passes this as `model`)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from .types import Plan


SYSTEM_PROMPT = """You are an expert Oracle Database DBA assistant.

Task: Convert the user's natural-language DBA request into a single Oracle SQL statement (or an anonymous PL/SQL block if needed).

Rules:
- Output MUST be valid JSON only (no markdown, no commentary).
- JSON schema:
  {
    \"classification\": \"read_only\" | \"dml\" | \"ddl\" | \"admin\" | \"unknown\",
    \"sql\": \"...\",
    \"binds\": {\"name\": value, ...},
    \"explanation\": \"...\",
    \"risks\": [\"...\", ...],
    \"requires_confirmation\": true|false
  }
- Prefer querying Oracle dynamic performance views (v$*) where appropriate.
- For potentially destructive operations (kill session, DDL, DML, ALTER SYSTEM, user/privilege changes), set requires_confirmation=true and include risks.
- Never invent schema objects. If a request depends on unknown schema/table names, produce a safe inspection query instead.
- Do not include credentials.
"""


def _openai_client():
    """Create an OpenAI client instance using `OPENAI_API_KEY`."""
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency 'openai'. Install with: pip install -r requirements.txt"
        ) from e
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _get_str(obj: Dict[str, Any], key: str) -> str:
    """Helper: pull a string field out of a dict; otherwise return empty string."""
    v = obj.get(key)
    return v if isinstance(v, str) else ""


def generate_plan(request: str, model: str) -> Plan:
    """Generate a `Plan` from a natural-language request.

    The model is instructed to return JSON only with keys:
    - classification, sql, binds, explanation, risks, requires_confirmation

    Returns:
    - Plan: a normalized plan with `sql` stripped and without a trailing ';'.

    Raises:
    - RuntimeError: if OpenAI client is missing or the model returns non-JSON.
    """
    client = _openai_client()

    # Prefer JSON mode when available to reduce invalid JSON responses.
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request},
            ],
        )
    except TypeError:
        # Older client/model that doesn't support response_format.
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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

    classification = _get_str(obj, "classification") or "unknown"
    sql = _get_str(obj, "sql")
    binds = obj.get("binds")
    explanation = _get_str(obj, "explanation")
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

"""Console/UI helpers for the CLI.

Keeping these helpers here makes the core logic (policy, OpenAI, execution)
testable and easier to reuse in other UIs later (web/Slack/etc).
"""

from __future__ import annotations

from typing import List, Tuple


def print_kv(title: str, kv: List[Tuple[str, str]]) -> None:
    """Pretty-print a small key/value list."""
    print(title)
    for k, v in kv:
        print(f"- {k}: {v}")


def prompt_confirm(prompt: str) -> bool:
    """Ask for a yes/no confirmation and return True only for explicit yes.

    Accepted yes values:
    - y
    - yes
    """
    ans = input(prompt).strip().lower()
    return ans in {"y", "yes"}

from __future__ import annotations

from typing import List, Tuple


def print_kv(title: str, kv: List[Tuple[str, str]]) -> None:
    print(title)
    for k, v in kv:
        print(f"- {k}: {v}")


def prompt_confirm(prompt: str) -> bool:
    ans = input(prompt).strip().lower()
    return ans in {"y", "yes"}

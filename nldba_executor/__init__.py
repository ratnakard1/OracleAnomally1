"""Natural-language DBA command executor (Oracle + OpenAI).

This package lets you:
- describe a DBA task in natural language
- generate Oracle SQL via OpenAI
- apply a local safety policy (block/confirm/allow)
- optionally execute against an Oracle database

Typical entrypoints:
- `python3 -m nldba_executor "..."`
- `from nldba_executor import main`
"""

from .cli import main

__all__ = ["main"]

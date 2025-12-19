"""Backward-compatible wrapper.

The implementation now lives in the `nldba_executor` package.

Usage:
- python3 nl_dba_executor.py "show blocking sessions"          (dry-run)
- python3 nl_dba_executor.py "kill session sid 123 serial 456" --execute
- python3 -m nldba_executor "show blocking sessions"

Note:
- This file exists so existing automation/scripts keep working after the refactor.
"""

from __future__ import annotations

from nldba_executor.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

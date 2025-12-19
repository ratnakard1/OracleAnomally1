"""Package entrypoint for `python -m nldba_executor`."""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())

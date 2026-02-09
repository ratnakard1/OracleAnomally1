#!/usr/bin/env python3
"""Oracle HugePages calculator based on SGA_MAX_SIZE.

Example:
    python test.py --sga-max-size 300G
"""

from __future__ import annotations

import argparse
import math
import re


_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMGTPE]?)(?:I?B)?\s*$", re.IGNORECASE)
_UNIT_TO_POWER = {
    "": 0,
    "K": 1,
    "M": 2,
    "G": 3,
    "T": 4,
    "P": 5,
    "E": 6,
}


def parse_size_to_bytes(size: str) -> int:
    """Parse sizes like 300G, 307200M, 322122547200 into bytes."""
    match = _SIZE_RE.match(size)
    if not match:
        raise ValueError(
            "Invalid size format. Use values like 300G, 307200M, or 322122547200."
        )

    value = float(match.group(1))
    unit = match.group(2).upper()
    power = _UNIT_TO_POWER[unit]
    return int(value * (1024**power))


def calculate_hugepages(
    sga_max_size_bytes: int,
    hugepage_size_kb: int = 2048,
    safety_buffer_pages: int = 0,
) -> int:
    """Return required vm.nr_hugepages for Oracle SGA allocation."""
    if sga_max_size_bytes <= 0:
        raise ValueError("SGA max size must be greater than 0.")
    if hugepage_size_kb <= 0:
        raise ValueError("HugePage size must be greater than 0.")
    if safety_buffer_pages < 0:
        raise ValueError("Safety buffer pages cannot be negative.")

    hugepage_size_bytes = hugepage_size_kb * 1024
    base_pages = math.ceil(sga_max_size_bytes / hugepage_size_bytes)
    return base_pages + safety_buffer_pages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate Oracle HugePages from SGA_MAX_SIZE."
    )
    parser.add_argument(
        "--sga-max-size",
        default="300G",
        help="Oracle SGA_MAX_SIZE value, e.g. 300G, 307200M, 322122547200.",
    )
    parser.add_argument(
        "--hugepage-size-kb",
        type=int,
        default=2048,
        help="HugePage size in KB from /proc/meminfo (default: 2048 for 2MB pages).",
    )
    parser.add_argument(
        "--safety-buffer-pages",
        type=int,
        default=0,
        help="Optional extra HugePages to reserve above the computed minimum.",
    )
    args = parser.parse_args()

    sga_max_size_bytes = parse_size_to_bytes(args.sga_max_size)
    hugepages = calculate_hugepages(
        sga_max_size_bytes=sga_max_size_bytes,
        hugepage_size_kb=args.hugepage_size_kb,
        safety_buffer_pages=args.safety_buffer_pages,
    )

    sga_gb = sga_max_size_bytes / (1024**3)
    hugepage_mb = args.hugepage_size_kb / 1024
    print(f"SGA_MAX_SIZE: {sga_gb:.2f} GiB")
    print(f"HugePage size: {hugepage_mb:.2f} MiB ({args.hugepage_size_kb} KB)")
    print(f"Required HugePages (vm.nr_hugepages): {hugepages}")


if __name__ == "__main__":
    main()

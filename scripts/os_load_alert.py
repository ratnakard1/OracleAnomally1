#!/usr/bin/env python3
"""Alert when OS load average exceeds a threshold."""

from __future__ import annotations

import argparse
import os
import sys

INTERVAL_INDEX = {1: 0, 5: 1, 15: 2}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Alert when OS load exceeds a threshold.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help="Alert threshold. When normalized (default), 0.90 == 90%.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        choices=sorted(INTERVAL_INDEX.keys()),
        default=1,
        help="Load average interval in minutes.",
    )
    parser.add_argument(
        "--cores",
        type=int,
        default=os.cpu_count() or 1,
        help="CPU cores used for normalization.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Compare raw load average without normalization.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print output when alerting.",
    )
    return parser.parse_args()


def get_load_average(interval: int) -> float:
    try:
        load_averages = os.getloadavg()
    except (AttributeError, OSError) as exc:
        raise RuntimeError(
            "Load average is not available on this platform."
        ) from exc
    return load_averages[INTERVAL_INDEX[interval]]


def main() -> int:
    args = parse_args()
    if args.cores <= 0:
        print("ERROR: --cores must be a positive integer.", file=sys.stderr)
        return 1

    try:
        load = get_load_average(args.interval)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.raw:
        value = load
        label = "raw"
    else:
        value = load / args.cores
        label = "normalized"

    alert = value > args.threshold
    if not args.quiet or alert:
        status = "ALERT" if alert else "OK"
        if args.raw:
            print(
                f"{status}: load {load:.2f} (interval {args.interval}m) "
                f"threshold {args.threshold:.2f}"
            )
        else:
            print(
                f"{status}: load {load:.2f} (interval {args.interval}m, "
                f"cores {args.cores}, {label} {value:.2f}) "
                f"threshold {args.threshold:.2f}"
            )

    return 2 if alert else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: os_load_alert.sh [options]

Options:
  --threshold VALUE   Alert threshold (default: 0.90).
  --interval MIN      Load average interval: 1, 5, or 15 (default: 1).
  --cores COUNT       CPU cores for normalization (default: system cores).
  --raw               Compare raw load average without normalization.
  --quiet             Only print output when alerting.
  -h, --help          Show this help and exit.

Examples:
  os_load_alert.sh --threshold 0.90 --interval 1
  os_load_alert.sh --raw --threshold 2.5
EOF
}

require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" ]]; then
    echo "ERROR: $opt requires a value." >&2
    usage >&2
    exit 2
  fi
}

threshold="0.90"
interval="1"
cores="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"
raw=false
quiet=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --threshold)
      require_value "$1" "${2:-}"
      threshold="$2"
      shift 2
      ;;
    --interval)
      require_value "$1" "${2:-}"
      interval="$2"
      shift 2
      ;;
    --cores)
      require_value "$1" "${2:-}"
      cores="$2"
      shift 2
      ;;
    --raw)
      raw=true
      shift
      ;;
    --quiet)
      quiet=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$cores" -le 0 ]]; then
  echo "ERROR: --cores must be a positive integer." >&2
  exit 2
fi

if [[ ! -r /proc/loadavg ]]; then
  echo "ERROR: /proc/loadavg is not readable on this system." >&2
  exit 1
fi

read -r load1 load5 load15 _ < /proc/loadavg
case "$interval" in
  1) load="$load1" ;;
  5) load="$load5" ;;
  15) load="$load15" ;;
  *)
    echo "ERROR: --interval must be 1, 5, or 15." >&2
    exit 2
    ;;
esac

load_display="$(awk -v l="$load" 'BEGIN { printf "%.2f", l }')"
threshold_display="$(awk -v t="$threshold" 'BEGIN { printf "%.2f", t }')"

if [[ "$raw" == true ]]; then
  value="$load"
  value_display="$load_display"
else
  value="$(awk -v l="$load" -v c="$cores" 'BEGIN { printf "%.6f", l / c }')"
  value_display="$(awk -v v="$value" 'BEGIN { printf "%.2f", v }')"
fi

alert="$(awk -v v="$value" -v t="$threshold" 'BEGIN { if (v > t) print 1; else print 0 }')"
status="OK"
code=0
if [[ "$alert" -eq 1 ]]; then
  status="ALERT"
  code=2
fi

if [[ "$quiet" == true && "$status" == "OK" ]]; then
  exit "$code"
fi

if [[ "$raw" == true ]]; then
  printf "%s: load %s (interval %sm) threshold %s\n" \
    "$status" "$load_display" "$interval" "$threshold_display"
else
  printf "%s: load %s (interval %sm, cores %s, normalized %s) threshold %s\n" \
    "$status" "$load_display" "$interval" "$cores" "$value_display" "$threshold_display"
fi

exit "$code"

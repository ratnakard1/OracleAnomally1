#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Run Oracle last-N-hours DB health report (AWR-based).

Usage:
  ./run_db_health_last24h.sh "<connect_string>" [hours_back] [top_n] [output_dir]

Examples:
  ./run_db_health_last24h.sh "/ as sysdba" 24 20 ./reports
  ./run_db_health_last24h.sh "system/password@//dbhost:1521/ORCLPDB1" 24 30 .

Notes:
  - The script spools a file named: db_health_last24h_<db_unique_name>_<timestamp>.lst
  - AWR sections require access to DBA_HIST_* (Diagnostics Pack licensing considerations apply).
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

CONNECT_STRING="${1:-/ as sysdba}"
HOURS_BACK="${2:-24}"
TOP_N="${3:-20}"
OUTPUT_DIR="${4:-.}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_SCRIPT="${SCRIPT_DIR}/db_health_last24h.sql"

if ! command -v sqlplus >/dev/null 2>&1; then
  echo "ERROR: sqlplus not found in PATH."
  echo "Install Oracle client (SQL*Plus) or run this from an Oracle DB server host."
  exit 127
fi

mkdir -p "${OUTPUT_DIR}"
cd "${OUTPUT_DIR}"

sqlplus -s "${CONNECT_STRING}" @"${SQL_SCRIPT}" "${HOURS_BACK}" "${TOP_N}"

echo "Done. Report written to: ${OUTPUT_DIR}/db_health_last24h_*.lst"


#!/usr/bin/env bash
# check_ogg_extract_hang.sh
# Alerts if Oracle GoldenGate Extract appears hung (RUNNING but checkpoint not advancing).
#
# User-provided inputs:
OGG_HOME="mmm"
DB_NAME="DB1"
ALERT_EMAIL="srinivt@amdocs.com"
#
# Tuning:
HANG_MINUTES=${HANG_MINUTES:-10}          # how long checkpoint must be unchanged to alert
ALERT_COOLDOWN_MINUTES=${ALERT_COOLDOWN_MINUTES:-60}  # minimum minutes between alerts per extract
STATE_DIR=${STATE_DIR:-"/tmp/ogg_extract_hang_${DB_NAME}"}
LOG_FILE=${LOG_FILE:-"${STATE_DIR}/check.log"}

set -euo pipefail

now_epoch=$(date +%s)
hang_seconds=$((HANG_MINUTES * 60))
cooldown_seconds=$((ALERT_COOLDOWN_MINUTES * 60))

mkdir -p "$STATE_DIR"

log() {
  printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG_FILE"
}

die() {
  log "ERROR: $*"
  echo "ERROR: $*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || die "Required file not found: $1"
}

send_mail() {
  local subject="$1"
  local body="$2"

  if command -v mailx >/dev/null 2>&1; then
    printf '%s\n' "$body" | mailx -s "$subject" "$ALERT_EMAIL" || true
  elif command -v mail >/dev/null 2>&1; then
    printf '%s\n' "$body" | mail -s "$subject" "$ALERT_EMAIL" || true
  elif command -v sendmail >/dev/null 2>&1; then
    {
      printf 'To: %s\n' "$ALERT_EMAIL"
      printf 'Subject: %s\n' "$subject"
      printf '\n'
      printf '%s\n' "$body"
    } | sendmail -t || true
  else
    log "WARN: No mail sender (mailx/mail/sendmail) found; cannot send alert"
  fi
}

GGSCI_BIN="$OGG_HOME/ggsci"
require_file "$GGSCI_BIN"

# Run GGSCI commands and capture output.
# Note: using a here-doc avoids issues with -e / special chars.
run_ggsci() {
  local script="$1"
  "$GGSCI_BIN" <<EOF
$script
EOF
}

# Extracts discovery: parse `info all` output.
# We intentionally avoid relying on fixed column offsets.
get_extracts() {
  # Print: <group_name> <status>
  run_ggsci "info all" 2>/dev/null | awk '
    BEGIN { in=0 }
    /^[[:space:]]*Program[[:space:]]+Status[[:space:]]+Group/ { in=1; next }
    in==1 && $1 ~ /^(EXTRACT|ER)$/ {
      # Typical: EXTRACT  RUNNING  EXT1
      print $3, $2
    }
  '
}

# Pull a stable checkpoint signature from `info extract <name>, showch`.
# Signature combines Seqno + RBA + timestamp line if present.
get_checkpoint_sig() {
  local ext="$1"

  # We look for the 'Log Read Checkpoint' block.
  run_ggsci "info extract ${ext}, showch" 2>/dev/null | awk '
    BEGIN { in=0; seq=""; rba=""; ts="" }
    /Log Read Checkpoint/ { in=1; next }
    in==1 {
      if ($1=="Seqno") seq=$2
      if ($1=="RBA") rba=$2
      # Some versions include: "Timestamp" "YYYY-MM-DD" "HH:MM:SS" ...
      if ($1=="Timestamp") {
        # store remainder as timestamp string
        ts=""
        for (i=2; i<=NF; i++) ts = ts (ts?" ":"") $i
      }
      # Stop once we reach a blank line or another section header.
      if ($0 ~ /^[[:space:]]*$/) { in=0 }
      if ($0 ~ /^[A-Z].*Checkpoint/ && $0 !~ /Log Read Checkpoint/) { in=0 }
    }
    END {
      if (seq=="" && rba=="") exit 2
      print "SEQ=" seq " RBA=" rba (ts?" TS=" ts:"")
    }
  '
}

alert_if_hung() {
  local ext="$1"
  local status="$2"

  # Only consider RUNNING extracts. If it isn't running, no "hang" alert.
  [[ "$status" == "RUNNING" ]] || return 0

  local sig
  if ! sig=$(get_checkpoint_sig "$ext"); then
    log "WARN: Could not read checkpoint for extract=$ext"
    return 0
  fi

  local state_file="$STATE_DIR/${ext}.state"
  local alert_file="$STATE_DIR/${ext}.last_alert"

  # state format: <epoch>|<sig>
  if [[ ! -f "$state_file" ]]; then
    printf '%s|%s\n' "$now_epoch" "$sig" >"$state_file"
    log "INIT: extract=$ext sig=[$sig]"
    return 0
  fi

  local prev_epoch prev_sig
  prev_epoch=$(cut -d'|' -f1 "$state_file" 2>/dev/null || echo 0)
  prev_sig=$(cut -d'|' -f2- "$state_file" 2>/dev/null || echo "")

  if [[ "$sig" != "$prev_sig" ]]; then
    printf '%s|%s\n' "$now_epoch" "$sig" >"$state_file"
    log "OK: extract=$ext advanced prev=[$prev_sig] now=[$sig]"
    return 0
  fi

  # unchanged: check how long it has been unchanged
  local unchanged_seconds=$((now_epoch - prev_epoch))
  if (( unchanged_seconds < hang_seconds )); then
    log "WAIT: extract=$ext unchanged_for=${unchanged_seconds}s threshold=${hang_seconds}s sig=[$sig]"
    return 0
  fi

  # Cooldown check to avoid spamming
  local last_alert=0
  if [[ -f "$alert_file" ]]; then
    last_alert=$(cat "$alert_file" 2>/dev/null || echo 0)
  fi
  if (( now_epoch - last_alert < cooldown_seconds )); then
    log "COOLDOWN: extract=$ext unchanged_for=${unchanged_seconds}s (alert suppressed)"
    return 0
  fi

  printf '%s\n' "$now_epoch" >"$alert_file"

  local minutes=$((unchanged_seconds / 60))
  local host
  host=$(hostname -f 2>/dev/null || hostname)

  local subject="[OGG][${DB_NAME}] Extract ${ext} possibly hung on ${host}"
  local body
  body=$(cat <<EOF
GoldenGate Extract hang alert

Host: ${host}
DB: ${DB_NAME}
OGG_HOME: ${OGG_HOME}
Extract: ${ext}
Status: ${status}

Checkpoint signature has NOT changed for ~${minutes} minute(s).
Signature: ${sig}

Action:
- Run: ${OGG_HOME}/ggsci
- Check: info extract ${ext}, detail
- Check: view report ${ext}

(Generated by check_ogg_extract_hang.sh)
EOF
)

  log "ALERT: extract=$ext unchanged_for=${minutes}m sig=[$sig]"
  send_mail "$subject" "$body"
}

main() {
  log "START: HANG_MINUTES=$HANG_MINUTES ALERT_COOLDOWN_MINUTES=$ALERT_COOLDOWN_MINUTES"

  local any=0
  while read -r ext status; do
    [[ -n "${ext:-}" ]] || continue
    any=1
    alert_if_hung "$ext" "$status"
  done < <(get_extracts)

  if (( any == 0 )); then
    log "INFO: No extracts found in 'info all' output"
  fi

  log "DONE"
}

main "$@"

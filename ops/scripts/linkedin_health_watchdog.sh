#!/usr/bin/env bash
set -Eeuo pipefail

# ==============================================================================
# CONFIGURATIONS - read-only LinkedIn health checks and Telegram alert dedupe
# ==============================================================================
PROJECT_DIR="${LINKEDIN_PROJECT_DIR:?Set LINKEDIN_PROJECT_DIR}"
LATEST_REPORT="${LINKEDIN_LATEST_REPORT:-$PROJECT_DIR/reports/runtime/linkedin_scheduler_latest.json}"
DATABASE="${LINKEDIN_OPERATIONAL_DB_ABSOLUTE:-$PROJECT_DIR/.agent/data/linkedin_operational.sqlite3}"
BROWSER_SERVICE="linkedin-browser.service"
SCHEDULER_TIMER="linkedin-scheduler.timer"
SCHEDULER_SERVICE="linkedin-scheduler.service"
STATE_DIR="${LINKEDIN_WATCHDOG_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/hermes/linkedin-watchdog}"
STATE_FILE="$STATE_DIR/last_alert.sha256"
MAX_REPORT_AGE_SECONDS=345600
# ==============================================================================


alert=""

append_alert() {
  local message="$1"
  if [[ -z "$alert" ]]; then
    alert="$message"
  else
    alert="$alert; $message"
  fi
}

if ! systemctl --user is-active --quiet "$SCHEDULER_TIMER"; then
  append_alert "scheduler timer inactive"
fi
if systemctl --user is-failed --quiet "$SCHEDULER_SERVICE"; then
  append_alert "scheduler service failed"
fi
if systemctl --user is-active --quiet "$BROWSER_SERVICE" && \
   ! systemctl --user is-active --quiet "$SCHEDULER_SERVICE"; then
  append_alert "browser unexpectedly active outside Warmup"
fi

if [[ -f "$LATEST_REPORT" ]]; then
  report_problem="$($PROJECT_DIR/.venv/bin/python -X utf8 - "$LATEST_REPORT" "$MAX_REPORT_AGE_SECONDS" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

path = Path(sys.argv[1])
maximum_age = int(sys.argv[2])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
    generated = datetime.fromisoformat(str(payload["generated_at"]))
    age = (datetime.now(timezone.utc) - generated.astimezone(timezone.utc)).total_seconds()
    state = str(payload.get("state", "UNKNOWN"))
    exit_code = int(payload.get("exit_code", 99))
    reason = str(payload.get("reason", ""))
    report_day = str(payload.get("local_day", ""))
    local_now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    healthy = {"SUCCESS", "OFF", "NOT_DUE", "SKIPPED", "DRY_RUN"}
    inherited_failure = state == "SKIPPED" and reason.startswith(
        "scheduler_day_already_recorded:"
    ) and reason.rsplit(":", 1)[-1] in {"FAILED", "BLOCKED", "PARTIAL", "UNCERTAIN"}
    if local_now.weekday() < 6 and local_now.hour >= 13 and report_day != local_now.date().isoformat():
        print(f"scheduler report missing for today ({local_now.date().isoformat()})")
    elif age > maximum_age:
        print(f"scheduler report stale ({int(age)}s)")
    elif exit_code != 0 or state not in healthy or inherited_failure:
        print(f"scheduler state={state} exit={exit_code} reason={reason}")
except Exception as exc:
    print(f"scheduler report unreadable ({type(exc).__name__})")
PY
)"
  [[ -z "$report_problem" ]] || append_alert "$report_problem"
else
  append_alert "scheduler report missing"
fi

if [[ -f "$DATABASE" ]]; then
  if ! "$PROJECT_DIR/.venv/bin/python" -X utf8 - "$DATABASE" <<'PY' >/dev/null 2>&1
import sqlite3
import sys

database = sys.argv[1]
connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=5)
try:
    result = connection.execute("PRAGMA quick_check").fetchone()
    if not result or result[0] != "ok":
        raise SystemExit(1)
finally:
    connection.close()
PY
  then
    append_alert "SQLite unavailable or integrity check failed"
  fi
else
  append_alert "SQLite database missing"
fi

mkdir -p "$STATE_DIR"
if [[ -z "$alert" ]]; then
  rm -f "$STATE_FILE"
  exit 0
fi

alert_hash="$(printf '%s' "$alert" | sha256sum | awk '{print $1}')"
previous_hash="$(cat "$STATE_FILE" 2>/dev/null || true)"
if [[ "$alert_hash" == "$previous_hash" ]]; then
  exit 0
fi
printf '%s\n' "$alert_hash" >"$STATE_FILE"
printf 'LinkedIn VPS alert: %s\n' "$alert"

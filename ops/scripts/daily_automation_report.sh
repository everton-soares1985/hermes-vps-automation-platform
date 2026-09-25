#!/usr/bin/env bash
set -Eeuo pipefail

# Required deployment settings. Keep real paths in the service environment,
# never in the repository.
export TZ="${AUTOMATION_TIMEZONE:-America/Sao_Paulo}"
: "${WELLFOUND_SAVED_ROOT:?Set WELLFOUND_SAVED_ROOT}"
: "${WELLFOUND_APPLY_ROOT:?Set WELLFOUND_APPLY_ROOT}"
: "${INFOJOBS_ROOT:?Set INFOJOBS_ROOT}"

today="$(date +%Y%m%d)"
today_iso="$(date +%F)"
now="$(date '+%Y-%m-%d %H:%M:%S %Z')"

python3 - "$today" "$today_iso" "$now" \
  "$WELLFOUND_SAVED_ROOT" "$WELLFOUND_APPLY_ROOT" "$INFOJOBS_ROOT" <<'PY'
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

day_compact, day_iso, now, saved_path, apply_path, info_path = sys.argv[1:7]
saved_root = Path(saved_path)
apply_root = Path(apply_path)
info_root = Path(info_path)


def latest(folder: Path, pattern: str) -> Path | None:
    candidates = list(folder.glob(pattern))
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha_short(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def count_value(value: object) -> int:
    return len(value) if isinstance(value, list) else int(value or 0)


def section(title: str) -> None:
    print(f"\n{title}")


def saved_summary() -> int | None:
    path = latest(saved_root / "logs", f"wellfound_saved_execute_saves_{day_compact}_*.json")
    section("WELLFOUND SAVED")
    if path is None:
        print("- Status: no official run completed today.")
        return None
    data = read_json(path)
    tabs = data.get("abas_processadas", [])
    details = [
        f"{tab.get('nome', '?')}: {int(tab.get('saves_confirmados', 0) or 0)}"
        for tab in tabs
    ]
    confirmed = int(data.get("saves_total_confirmados", 0) or 0)
    failed = int(data.get("saves_total_falhos", 0) or 0)
    print(f"- Saved jobs: {confirmed} ({'; '.join(details)}).")
    print(f"- Failed save actions: {failed}.")
    print("- Applications: 0 (this workflow never submits applications).")
    print(f"- Evidence: {path.name} | sha256 {sha_short(path)}...")
    return confirmed


def apply_confirmed_from_ledger() -> int | None:
    database = apply_root / ".agent" / "data" / "wellfound_apply_operational.sqlite3"
    if not database.exists():
        return None
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM job_ledger WHERE status = ? AND local_day = ?",
                ("APPLIED_CONFIRMED", day_iso),
            ).fetchone()
        return int(row[0])
    except sqlite3.Error:
        return None


def apply_summary() -> int | None:
    folder = apply_root / ".agent" / "scripts" / "logs"
    path = latest(folder, f"wellfound_apply_safe_base_{day_compact}_*.json")
    section("WELLFOUND APPLY")
    if path is None:
        print("- Status: no official run completed today.")
        return None
    data = read_json(path)
    ledger_confirmed = apply_confirmed_from_ledger()
    submitted = int(data.get("applications_submitted", 0) or 0)
    processed = int(data.get("batch_jobs_processed", 0) or 0)
    blocked = int(data.get("batch_complex_blocked", 0) or 0)
    errors = count_value(data.get("batch_errors", data.get("errors", [])))
    confirmed = ledger_confirmed if ledger_confirmed is not None else submitted
    print(f"- Confirmed applications today: {confirmed}.")
    print(f"- Examined: {processed}; complex forms blocked: {blocked}; errors: {errors}.")
    print(f"- Evidence: {path.name} | sha256 {sha_short(path)}...")
    return confirmed


def infojobs_summary() -> int | None:
    folder = info_root / ".agent" / "reports" / "infojobs"
    path = latest(folder, f"{day_compact}_*.json")
    section("INFOJOBS")
    if path is None:
        print("- Status: no official run completed today.")
        return None
    data = read_json(path)
    confirmed = int(data.get("confirmed", 0) or 0)
    examined = int(data.get("jobs_examined", 0) or 0)
    target = int(data.get("target", 0) or 0)
    stop_reason = data.get("stop_reason") or "not reported"
    print(f"- State: {str(data.get('state', 'unknown')).lower()}.")
    print(f"- Confirmed: {confirmed}/{target}; examined: {examined}.")
    print(f"- Stop reason: {stop_reason}.")
    print(f"- Evidence: {path.name} | sha256 {sha_short(path)}...")
    return confirmed


print(f"DAILY AUTOMATION REPORT - {now}")
print("Source: official JSON evidence and read-only SQLite ledgers.")
saved_count = saved_summary()
apply_count = apply_summary()
info_count = infojobs_summary()

section("DAILY SUMMARY")
print(f"- Wellfound Saved: {saved_count if saved_count is not None else 'no run'}.")
print(f"- Wellfound Apply: {apply_count if apply_count is not None else 'no run'}.")
print(f"- InfoJobs: {info_count if info_count is not None else 'no run'}.")
PY

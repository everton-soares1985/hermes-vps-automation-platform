#!/usr/bin/env bash
set -Eeuo pipefail
export TZ="${AUTOMATION_TIMEZONE:-America/Sao_Paulo}"
cd "${WELLFOUND_SAVED_ROOT:?Set WELLFOUND_SAVED_ROOT}"
exec ./wellfound_control.sh save --confirm-save --max-total 150 --max-per-tab 50 Growth Web3 Automation

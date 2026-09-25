#!/usr/bin/env bash
set -Eeuo pipefail
export TZ="${AUTOMATION_TIMEZONE:-America/Sao_Paulo}"
cd "${WELLFOUND_APPLY_ROOT:?Set WELLFOUND_APPLY_ROOT}"
exec ./wellfound_apply_control.sh start-apply --confirm-apply 30

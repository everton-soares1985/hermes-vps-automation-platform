#!/usr/bin/env bash
# =============================================================================
# Daily external-saved cleanup. No AI, form filling, or submission.
# Schedule one hour after the Saved workflow starts.
# =============================================================================
set -Eeuo pipefail
export TZ="${AUTOMATION_TIMEZONE:-America/Sao_Paulo}"

cd "${WELLFOUND_APPLY_ROOT:?Set WELLFOUND_APPLY_ROOT}"
exec ./wellfound_apply_control.sh start-cleanup --confirm-cleanup

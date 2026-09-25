#!/usr/bin/env bash
set -u
export TZ="${AUTOMATION_TIMEZONE:-America/Sao_Paulo}"
issues=()
systemctl --user is-active --quiet hermes-gateway.service || issues+=("Hermes Gateway")
systemctl --user is-active --quiet wellfound-browser.service || issues+=("Wellfound browser")
systemctl --user is-active --quiet infojobs-browser.service || issues+=("InfoJobs browser")
curl -fsS "${WELLFOUND_CDP_URL:-http://127.0.0.1:9224/json/version}" >/dev/null || issues+=("Wellfound CDP")
curl -fsS "${INFOJOBS_CDP_URL:-http://127.0.0.1:9226/json/version}" >/dev/null || issues+=("InfoJobs CDP")
mem_kb=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
(( mem_kb >= 1048576 )) || issues+=("RAM below 1 GiB available")
disk_pct=$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')
(( disk_pct < 85 )) || issues+=("disk root at ${disk_pct}%")
if (( ${#issues[@]} )); then
  printf 'VPS ALERT %s\n- %s\n' "$(date '+%F %T %Z')" "$(IFS=$'\n- '; echo "${issues[*]}")"
fi

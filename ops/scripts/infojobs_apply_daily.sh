#!/usr/bin/env bash
set -Eeuo pipefail
export TZ="${AUTOMATION_TIMEZONE:-America/Sao_Paulo}"
day="$(date +%u)"
case "$day" in
  1) query="Desenvolvedor Python"; location="Todo Brasil" ;;
  2) query="Desenvolvedor de Software"; location="Sao Paulo - SP" ;;
  3) query="Automacao de Processos"; location="Todo Brasil" ;;
  4) query="Inteligencia Artificial"; location="Sao Paulo - SP" ;;
  5) query="Engenheiro de Dados"; location="Todo Brasil" ;;
  6) query="Desenvolvedor Back-end"; location="Sao Paulo - SP" ;;
  7) query="DevOps Cloud"; location="Todo Brasil" ;;
esac
printf 'INFOJOBS_PLAN day=%s query=%s location=%s target=15 scan_limit=40\n' "$day" "$query" "$location"
cd "${INFOJOBS_ROOT:?Set INFOJOBS_ROOT}"
exec ./infojobs_control.sh start-apply --confirm-apply 15 --query "$query" --location "$location" --scan-limit 40

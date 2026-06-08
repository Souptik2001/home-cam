#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="/run/home-cam-network-failures"
MAX_FAILURES=3
TARGET="192.168.29.1"

if ping -c 2 -W 3 "$TARGET" >/dev/null 2>&1; then
  rm -f "$STATE_FILE"
  exit 0
fi

failures=0
if [[ -f "$STATE_FILE" ]]; then
  failures="$(cat "$STATE_FILE")"
fi

failures=$((failures + 1))
echo "$failures" > "$STATE_FILE"

logger -t home-cam-watchdog "Network check failed for $TARGET ($failures/$MAX_FAILURES)"

if [[ "$failures" -eq 2 ]]; then
  if systemctl cat NetworkManager.service >/dev/null 2>&1; then
    systemctl restart NetworkManager || true
  elif systemctl cat dhcpcd.service >/dev/null 2>&1; then
    systemctl restart dhcpcd || true
  fi
  exit 0
fi

if [[ "$failures" -ge "$MAX_FAILURES" ]]; then
  logger -t home-cam-watchdog "Network unavailable after $failures checks; rebooting"
  systemctl reboot
fi

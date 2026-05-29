#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/../.." || exit 1

if [[ -f scripts/demo/_ff-proof-lib.sh ]]; then
  source scripts/demo/_ff-proof-lib.sh
fi

if declare -F cleanup_stale_proof_processes >/dev/null 2>&1; then
  cleanup_stale_proof_processes
else
  echo "Cleaning stale proof/browser processes..."
  pkill -TERM -f 'node .*scripts/(hoi|campaign-payment-smoke|ff_visual_launch_gate)' 2>/dev/null || true
  pkill -TERM -f 'chrome-headless-shell|chromium_headless_shell|ms-playwright' 2>/dev/null || true
  sleep 2
  pkill -KILL -f 'node .*scripts/(hoi|campaign-payment-smoke|ff_visual_launch_gate)' 2>/dev/null || true
  pkill -KILL -f 'chrome-headless-shell|chromium_headless_shell|ms-playwright' 2>/dev/null || true
fi

if declare -F proof_snapshot >/dev/null 2>&1; then
  proof_snapshot
else
  echo
  echo "Proof process snapshot:"
  ps -eo pid,ppid,stat,etime,pcpu,pmem,command \
    | grep -E 'futurefunded-web|flask --app|cloudflared tunnel|chrome-headless-shell|chromium_headless_shell|ms-playwright|node .*scripts/(hoi|campaign-payment-smoke|ff_visual_launch_gate)' \
    | grep -v grep || true
fi

echo
echo "Proof cleanup complete."

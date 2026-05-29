#!/usr/bin/env bash

: "${FF_BASE_URL:=http://127.0.0.1:5000}"

FF_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
FF_PROOF_DIR="$FF_ROOT/audit_outputs/demo-proof/latest"
mkdir -p "$FF_PROOF_DIR"

cleanup_stale_proof_processes() {
  echo "Cleaning stale proof/browser processes..."

  pkill -TERM -f 'node .*scripts/(hoi|campaign-payment-smoke|release/ff_visual_launch_gate)' 2>/dev/null || true
  pkill -TERM -f 'chrome-headless-shell' 2>/dev/null || true
  pkill -TERM -f 'chromium_headless_shell' 2>/dev/null || true
  pkill -TERM -f 'ms-playwright' 2>/dev/null || true

  sleep 2

  pkill -KILL -f 'node .*scripts/(hoi|campaign-payment-smoke|release/ff_visual_launch_gate)' 2>/dev/null || true
  pkill -KILL -f 'chrome-headless-shell' 2>/dev/null || true
  pkill -KILL -f 'chromium_headless_shell' 2>/dev/null || true
  pkill -KILL -f 'ms-playwright' 2>/dev/null || true
}

proof_snapshot() {
  echo
  echo "Proof process snapshot:"
  ps -eo pid,ppid,stat,etime,pcpu,pmem,command \
    | grep -E 'futurefunded-web|flask --app|cloudflared tunnel|chrome-headless-shell|chromium_headless_shell|ms-playwright|node .*scripts/(hoi|campaign-payment-smoke|ff_visual_launch_gate)' \
    | grep -v grep || true
}

ensure_operator_token() {
  if [[ ! -s /tmp/ff_operator_token ]]; then
    python - <<'PY'
from pathlib import Path
import secrets
Path("/tmp/ff_operator_token").write_text(secrets.token_urlsafe(32))
print("Created /tmp/ff_operator_token")
PY
  fi

  # Marker: hoi-demo-proof-token-preserve-v1
if [ -z "${FF_OPERATOR_ACCESS_TOKEN:-}" ]; then
  export FF_OPERATOR_ACCESS_TOKEN="$(cat /tmp/ff_operator_token 2>/dev/null || true)"
fi
if [ -z "${OPERATOR_ACCESS_TOKEN:-}" ]; then
  export OPERATOR_ACCESS_TOKEN="${FF_OPERATOR_ACCESS_TOKEN:-}"
fi
}

health_ok() {
  curl -fsS "$FF_BASE_URL/healthz" >/dev/null 2>&1
}

ensure_pm2_web() {
  cd "$FF_ROOT"

  ensure_operator_token

  export FF_BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
  export FF_ASSET_V="${FF_ASSET_V:-proof-$(date +%Y%m%d%H%M%S)}"
  export STRIPE_LIVE_MODE="${STRIPE_LIVE_MODE:-0}"
  export FF_PAYMENTS_ENABLED="${FF_PAYMENTS_ENABLED:-1}"
  export FF_EXPECT_TEST_PAYMENTS="${FF_EXPECT_TEST_PAYMENTS:-1}"
  export FF_FORBID_LIVE_KEYS="${FF_FORBID_LIVE_KEYS:-1}"

  if health_ok; then
    return 0
  fi

  echo "App health is not ready. Ensuring PM2 web process exists..."

  if pm2 describe futurefunded-web >/dev/null 2>&1; then
    pm2 restart futurefunded-web --update-env >/dev/null
  else
    pm2 start "$FF_ROOT/.venv/bin/python" \
      --name futurefunded-web \
      --interpreter none \
      --cwd "$FF_ROOT" \
      -- \
      -m flask --app 'apps.web.app:create_app()' run \
      --host 127.0.0.1 \
      --port 5000 \
      --no-debugger \
      --no-reload >/dev/null
  fi
}

wait_for_health() {
  cd "$FF_ROOT"

  echo "Waiting for app health: $FF_BASE_URL/healthz"

  ensure_pm2_web

  local max="${FF_HEALTH_TIMEOUT:-45}"
  local start
  start="$(date +%s)"

  while true; do
    if health_ok; then
      echo "Health check passed."
      return 0
    fi

    if (( $(date +%s) - start >= max )); then
      echo "❌ Health check failed after ${max}s."
      proof_snapshot
      echo
      echo "Recent PM2 logs:"
      pm2 logs futurefunded-web --lines 120 --nostream || true
      return 1
    fi

    sleep 1
  done
}

run_step() {
  local label="$1"
  local seconds="$2"
  local cmd="$3"
  local slug
  slug="$(echo "$label" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')"
  local log="$FF_PROOF_DIR/${slug}.log"

  echo
  echo "================================================================"
  echo "▶ $label"
  echo "Timeout: ${seconds}s"
  echo "Log: $log"
  echo "================================================================"

  cleanup_stale_proof_processes >/dev/null 2>&1 || true

  set +e
  timeout --kill-after=20s "${seconds}s" bash -lc "$cmd" 2>&1 | tee "$log"
  local status="${PIPESTATUS[0]}"
  set -e

  cleanup_stale_proof_processes >/dev/null 2>&1 || true

  if [[ "$status" -ne 0 ]]; then
    echo "❌ FAILED: $label exited with code $status."
    proof_snapshot
    echo
    echo "Last 120 log lines:"
    tail -120 "$log" || true
    return "$status"
  fi

  echo "✅ PASSED: $label"
}

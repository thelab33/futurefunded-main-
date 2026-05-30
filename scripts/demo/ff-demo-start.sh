#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.nvm/versions/node/v20.20.1/bin:$PATH"
export VIRTUAL_ENV="${VIRTUAL_ENV-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5000}"
BASE_URL="http://${HOST}:${PORT}"
LOG_DIR="$ROOT/audit_outputs/dev-server"
LOG_FILE="$LOG_DIR/latest.log"
PID_FILE="$LOG_DIR/latest.pid"

mkdir -p "$LOG_DIR"

echo "== FutureFunded clean-root demo start =="
echo "ROOT=$ROOT"
echo "URL=$BASE_URL"

# Kill stale Flask servers from any FutureFunded repo.
pkill -f "/futurefunded-product-spine/.venv/bin/python -m flask" 2>/dev/null || true
pkill -f "/futurefunded-final/.venv/bin/python -m flask" 2>/dev/null || true
pkill -f "/futurefunded-main/.venv/bin/python -m flask" 2>/dev/null || true
pkill -f "flask --app apps.web.app:create_app run --host ${HOST} --port ${PORT}" 2>/dev/null || true

if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
fi

sleep 1

PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="$(command -v python3 || command -v python)"
fi

export FLASK_APP="apps.web.app:create_app"
export FF_DEMO_MODE="${FF_DEMO_MODE:-1}"
export FF_PAYMENTS_ENABLED="${FF_PAYMENTS_ENABLED:-1}"
export FF_EXPECT_TEST_PAYMENTS="${FF_EXPECT_TEST_PAYMENTS:-1}"
export FF_FORBID_LIVE_KEYS="${FF_FORBID_LIVE_KEYS:-1}"
export FF_OPERATOR_TOKEN="${FF_OPERATOR_TOKEN:-dev-operator-20260529123018}"

nohup "$PY" -m flask --app apps.web.app:create_app run \
  --host "$HOST" \
  --port "$PORT" \
  --no-debugger \
  --no-reload \
  > "$LOG_FILE" 2>&1 &

PID="$!"
echo "$PID" > "$PID_FILE"

# Health check using Python so we do not depend on curl.
for i in $(seq 1 40); do
  if "$PY" - <<PY >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("${BASE_URL}/healthz", timeout=1).read()
PY
  then
    echo
    echo "✅ FutureFunded local demo is running from clean root."
    echo
    echo "Open:"
    echo "  Platform:   ${BASE_URL}/platform/"
    echo "  Campaign:   ${BASE_URL}/c/connect-atx-elite"
    echo "  Login:      ${BASE_URL}/platform/login"
    echo "  Onboarding: ${BASE_URL}/platform/onboarding"
    echo "  Dashboard:  ${BASE_URL}/platform/dashboard?access_token=${FF_OPERATOR_TOKEN}"
    echo
    echo "Proof command:"
    echo "  bash scripts/demo/ff-fast-proof-strict.sh"
    echo
    echo "PID: $PID"
    echo "Log: $LOG_FILE"
    exit 0
  fi
  sleep 0.5
done

echo "❌ FutureFunded demo failed to become healthy."
echo "Log: $LOG_FILE"
tail -120 "$LOG_FILE" || true
exit 1

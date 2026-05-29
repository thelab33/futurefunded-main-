#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

export PYTHONPATH="${PWD}:${PYTHONPATH:-}"
export PORT="${PORT:-5050}"

LOG="artifacts/gunicorn-boot.log"
mkdir -p artifacts

lsof -ti tcp:"$PORT" | xargs -r kill

gunicorn apps.web.wsgi:app \
  --bind "127.0.0.1:${PORT}" \
  --workers 1 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  >"$LOG" 2>&1 &

PID="$!"
cleanup() {
  kill "$PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 4

curl -fsSIL "http://127.0.0.1:${PORT}/platform/" >/dev/null
curl -fsSIL "http://127.0.0.1:${PORT}/c/connect-atx-elite" >/dev/null

echo "OK: Gunicorn booted and served FutureFunded on port ${PORT}"

#!/usr/bin/env bash
set -euo pipefail

CLEAN_ROOT="$HOME/futurefunded-main"
OLD_ROOT="$HOME/futurefunded-product-spine"
PORT="${PORT:-5000}"
OLD_PORT="${OLD_PORT:-5010}"

status() {
  echo "== FutureFunded server status =="
  echo
  echo "Port $PORT:"
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  echo
  echo "Port $OLD_PORT:"
  lsof -nP -iTCP:"$OLD_PORT" -sTCP:LISTEN || true
  echo
  echo "Processes:"
  ps -eo pid,ppid,etime,cmd \
    | grep -E "python -m flask|flask --app|futurefunded-main|futurefunded-product-spine|cloudflared" \
    | grep -v grep || true
}

stop() {
  echo "== Stopping FutureFunded local servers =="
  pkill -f "/futurefunded-product-spine/.venv/bin/python -m flask" 2>/dev/null || true
  pkill -f "/futurefunded-final/.venv/bin/python -m flask" 2>/dev/null || true
  pkill -f "/futurefunded-main/.venv/bin/python -m flask" 2>/dev/null || true
  pkill -f "flask --app apps.web.app:create_app run --host 127.0.0.1 --port $PORT" 2>/dev/null || true
  pkill -f "flask --app apps.web.app:create_app run --host 127.0.0.1 --port $OLD_PORT" 2>/dev/null || true
  fuser -k "$PORT/tcp" 2>/dev/null || true
  fuser -k "$OLD_PORT/tcp" 2>/dev/null || true
  sleep 1
  echo "✅ stopped"
}

start() {
  echo "== Starting clean FutureFunded server =="
  cd "$CLEAN_ROOT" || exit 1
  source .venv/bin/activate 2>/dev/null || true

  fuser -k "$PORT/tcp" 2>/dev/null || true
  sleep 1

  bash scripts/demo/ff-demo-start.sh

  echo
  echo "== Route smoke =="
  for path in /healthz /platform/ /platform/onboarding /platform/login /c/connect-atx-elite; do
    curl -fsS -o /dev/null -w "%{http_code}  $path\n" "http://127.0.0.1:${PORT}${path}"
  done

  echo
  echo "✅ clean server ready: http://127.0.0.1:${PORT}/c/connect-atx-elite"
}

restart() {
  stop
  start
}

old_start() {
  echo "== Starting OLD repo on isolated port $OLD_PORT =="
  echo "This is for reference only. Do not use old repo for launch."
  cd "$OLD_ROOT" || exit 1
  source .venv/bin/activate 2>/dev/null || true

  fuser -k "$OLD_PORT/tcp" 2>/dev/null || true
  sleep 1

  nohup python -m flask --app apps.web.app:create_app run \
    --host 127.0.0.1 \
    --port "$OLD_PORT" \
    --no-debugger \
    --no-reload \
    > /tmp/futurefunded-old-repo-5010.log 2>&1 &

  sleep 3

  echo "Old repo URL: http://127.0.0.1:${OLD_PORT}/c/connect-atx-elite"
  echo "Old repo log: /tmp/futurefunded-old-repo-5010.log"
  curl -fsS -o /dev/null -w "%{http_code}  /healthz\n" "http://127.0.0.1:${OLD_PORT}/healthz" || true
}

case "${1:-status}" in
  status) status ;;
  stop) stop ;;
  start) start ;;
  restart) restart ;;
  old-start) old_start ;;
  *)
    echo "Usage: ff-server-control.sh {status|stop|start|restart|old-start}"
    exit 2
    ;;
esac

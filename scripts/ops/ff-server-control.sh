#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/.nvm/versions/node/v20.20.1/bin:$PATH"
export VIRTUAL_ENV="${VIRTUAL_ENV-}"

CLEAN_ROOT="$HOME/futurefunded-main"
OLD_ROOT="$HOME/futurefunded-product-spine"
PORT="${PORT:-5000}"
OLD_PORT="${OLD_PORT:-5010}"

kill_port() {
  local port="$1"
  local pids
  pids="$(/usr/bin/lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Killing listeners on port $port: $pids"
    echo "$pids" | xargs -r kill -TERM 2>/dev/null || true
    sleep 1
    echo "$pids" | xargs -r kill -KILL 2>/dev/null || true
  fi
}

stop_supervisors() {
  if command -v pm2 >/dev/null 2>&1; then
    pm2 delete futurefunded-product-spine-web 2>/dev/null || true
    pm2 delete futurefunded-web 2>/dev/null || true
    pm2 save --force 2>/dev/null || true
  fi
}

status() {
  echo "== FutureFunded server status =="
  echo
  echo "Clean root: $CLEAN_ROOT"
  echo "Old root:   $OLD_ROOT"
  echo
  echo "Port $PORT:"
  /usr/bin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  echo
  echo "Port $OLD_PORT:"
  /usr/bin/lsof -nP -iTCP:"$OLD_PORT" -sTCP:LISTEN || true
  echo
  echo "Processes:"
  /bin/ps -eo pid,ppid,etime,cmd \
    | /usr/bin/grep -E "python -m flask|flask --app|futurefunded-main|futurefunded-product-spine|pm2|cloudflared" \
    | /usr/bin/grep -v grep || true
}

stop() {
  echo "== Stopping FutureFunded local servers =="
  stop_supervisors

  /usr/bin/pkill -TERM -f "futurefunded-product-spine.*flask" 2>/dev/null || true
  /usr/bin/pkill -TERM -f "futurefunded-main.*flask" 2>/dev/null || true
  /usr/bin/pkill -TERM -f "flask --app apps.web.app:create_app" 2>/dev/null || true
  sleep 1

  /usr/bin/pkill -KILL -f "futurefunded-product-spine.*flask" 2>/dev/null || true
  /usr/bin/pkill -KILL -f "futurefunded-main.*flask" 2>/dev/null || true
  /usr/bin/pkill -KILL -f "flask --app apps.web.app:create_app" 2>/dev/null || true

  kill_port "$PORT"
  kill_port "$OLD_PORT"

  echo "✅ stopped"
}

start() {
  echo "== Starting clean FutureFunded server =="
  stop

  cd "$CLEAN_ROOT" || exit 1
  source .venv/bin/activate 2>/dev/null || true
  bash scripts/demo/ff-demo-start.sh

  echo
  echo "== Route smoke =="
  for path in /healthz /platform/ /platform/onboarding /platform/login /c/connect-atx-elite; do
    /usr/bin/curl -fsS -o /dev/null -w "%{http_code}  $path\n" "http://127.0.0.1:${PORT}${path}"
  done

  echo
  echo "== Owner check =="
  status

  if /bin/ps -eo pid,cmd | /usr/bin/grep -E "futurefunded-product-spine.*python -m flask.*port ${PORT}" | /usr/bin/grep -v grep; then
    echo "❌ Old repo still owns port $PORT."
    exit 1
  fi

  echo
  echo "✅ clean server ready: http://127.0.0.1:${PORT}/c/connect-atx-elite"
}

restart() {
  start
}

old_start() {
  echo "== Starting OLD repo on isolated port $OLD_PORT =="
  echo "Reference only. Do not use old repo for launch."

  kill_port "$OLD_PORT"

  cd "$OLD_ROOT" || exit 1
  source .venv/bin/activate 2>/dev/null || true

  nohup python -m flask --app apps.web.app:create_app run \
    --host 127.0.0.1 \
    --port "$OLD_PORT" \
    --no-debugger \
    --no-reload \
    > /tmp/futurefunded-old-repo-5010.log 2>&1 &

  sleep 3
  echo "Old repo URL: http://127.0.0.1:${OLD_PORT}/c/connect-atx-elite"
  echo "Old repo log: /tmp/futurefunded-old-repo-5010.log"
}

case "${1:-status}" in
  status) status ;;
  stop) stop ;;
  start) start ;;
  restart) restart ;;
  old-start) old_start ;;
  *)
    echo "Usage: ffserver {status|stop|start|restart|old-start}"
    exit 2
    ;;
esac

#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

mkdir -p /tmp/futurefunded

export FF_OPERATOR_ACCESS_TOKEN="${FF_OPERATOR_ACCESS_TOKEN:-$(cat /tmp/ff_operator_token 2>/dev/null || echo dev_operator_local)}"

echo "== stopping old local Flask on 5000 =="
fuser -k 5000/tcp 2>/dev/null || true

echo "== starting Flask origin on 127.0.0.1:5000 =="
nohup python -m flask --app apps.web.app --debug run \
  --host 127.0.0.1 \
  --port 5000 \
  --no-reload \
  > /tmp/futurefunded/flask.log 2>&1 &

echo $! > /tmp/futurefunded/flask.pid

echo "== waiting for Flask origin =="
for i in {1..40}; do
  if curl -fsS "http://127.0.0.1:5000/c/connect-atx-elite" >/dev/null; then
    echo "OK local origin is up"
    break
  fi

  if ! kill -0 "$(cat /tmp/futurefunded/flask.pid)" 2>/dev/null; then
    echo "Flask exited early. Last logs:"
    tail -80 /tmp/futurefunded/flask.log || true
    exit 1
  fi

  sleep 1
done

curl -fsS "http://127.0.0.1:5000/c/connect-atx-elite" >/dev/null || {
  echo "Flask did not become reachable. Last logs:"
  tail -80 /tmp/futurefunded/flask.log || true
  exit 1
}

echo
echo "Flask PID: $(cat /tmp/futurefunded/flask.pid)"
echo "Flask log: /tmp/futurefunded/flask.log"
echo
echo "Now run this in another terminal:"
echo "  cloudflared tunnel run futurefunded-prod"
echo
echo "Then verify:"
echo "  curl -I https://getfuturefunded.com/c/connect-atx-elite"
echo "  CAMPAIGN_URL='https://getfuturefunded.com/c/connect-atx-elite' SMOKE_VIEWPORTS=mobile node scripts/campaign-payment-smoke.mjs"

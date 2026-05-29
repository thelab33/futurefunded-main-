#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env.local ]; then
  set -a
  . ./.env.local
  set +a
fi

if [ -s .stripe-local-whsec ]; then
  export FF_STRIPE_WEBHOOK_SECRET="$(cat .stripe-local-whsec)"
fi

export STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-${FF_STRIPE_WEBHOOK_SECRET:-}}"
export STRIPE_WEBHOOK_SIGNING_SECRET="${STRIPE_WEBHOOK_SIGNING_SECRET:-${FF_STRIPE_WEBHOOK_SECRET:-}}"
export FF_STRIPE_WEBHOOK_SECRET="${FF_STRIPE_WEBHOOK_SECRET:-${STRIPE_WEBHOOK_SECRET:-${STRIPE_WEBHOOK_SIGNING_SECRET:-}}}"

if [ -z "${FF_OPERATOR_ACCESS_TOKEN:-}" ]; then
  if [ -s /tmp/ff_operator_token ]; then
    export FF_OPERATOR_ACCESS_TOKEN="$(cat /tmp/ff_operator_token)"
  else
    export FF_OPERATOR_ACCESS_TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  fi
fi

printf "%s" "$FF_OPERATOR_ACCESS_TOKEN" > /tmp/ff_operator_token
chmod 600 /tmp/ff_operator_token

python - <<'PY'
import os, sys

errors = []

stripe = os.environ.get("STRIPE_SECRET_KEY", "")
if not stripe.startswith(("sk_test_", "sk_live_")):
    errors.append("STRIPE_SECRET_KEY missing or invalid")

webhook = (
    os.environ.get("FF_STRIPE_WEBHOOK_SECRET")
    or os.environ.get("STRIPE_WEBHOOK_SECRET")
    or os.environ.get("STRIPE_WEBHOOK_SIGNING_SECRET")
    or ""
)
if not webhook.startswith("whsec_"):
    errors.append("Webhook secret missing or invalid")

token = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "")
if len(token) < 16:
    errors.append("FF_OPERATOR_ACCESS_TOKEN missing or too short")

if errors:
    print("Cannot start FutureFunded local server:")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print("FutureFunded verified local server")
print(f"Stripe key loaded: {stripe[:8]}…")
print(f"Webhook secret loaded: {webhook[:8]}…")
print(f"Operator token loaded: {token[:8]}…")
PY

lsof -ti tcp:5000 | xargs -r kill -9
sleep 1

exec python -m flask --app apps.web.app --debug run \
  --host 127.0.0.1 \
  --port 5000 \
  --no-reload

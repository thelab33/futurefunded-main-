#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env.local ]; then
  set -a
  . ./.env.local
  set +a
fi

if [ -z "${STRIPE_SECRET_KEY:-}" ]; then
  echo "Missing STRIPE_SECRET_KEY."
  echo "Create .env.local with:"
  echo "STRIPE_SECRET_KEY=sk_test_..."
  exit 1
fi

if [ -z "${FF_STRIPE_WEBHOOK_SECRET:-${STRIPE_WEBHOOK_SECRET:-${STRIPE_WEBHOOK_SIGNING_SECRET:-}}}" ] && [ -f .stripe-local-whsec ]; then
  if [ -s .stripe-local-whsec ]; then
  export FF_STRIPE_WEBHOOK_SECRET="$(cat .stripe-local-whsec)"
fi

if [ -s /tmp/ff_operator_token ]; then
  export FF_OPERATOR_ACCESS_TOKEN="$(cat /tmp/ff_operator_token)"
fi

export STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-${FF_STRIPE_WEBHOOK_SECRET:-}}"
export FF_STRIPE_WEBHOOK_SECRET="${FF_STRIPE_WEBHOOK_SECRET:-${STRIPE_WEBHOOK_SECRET:-${STRIPE_WEBHOOK_SIGNING_SECRET:-}}}"
export STRIPE_WEBHOOK_SIGNING_SECRET="${STRIPE_WEBHOOK_SIGNING_SECRET:-${FF_STRIPE_WEBHOOK_SECRET:-}}"
export FF_OPERATOR_ACCESS_TOKEN="${FF_OPERATOR_ACCESS_TOKEN:-dev_operator_local}"

echo "FutureFunded local server"
echo "Stripe key loaded: ${STRIPE_SECRET_KEY:0:8}…"
echo "Operator token loaded: yes"
echo "Webhook secret loaded: $([ -n "${FF_STRIPE_WEBHOOK_SECRET:-}" ] && echo yes || echo no)"

python -m flask --app apps.web.app --debug run \
  --host 127.0.0.1 \
  --port 5000 \
  --no-reload

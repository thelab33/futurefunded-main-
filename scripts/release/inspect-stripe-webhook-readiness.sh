#!/usr/bin/env bash
set -euo pipefail

echo "FutureFunded Stripe webhook readiness"
echo

echo "=== Route/code search ==="
rg -n "stripe/webhook|webhook|WEBHOOK_SECRET|ENDPOINT_SECRET|construct_event|Stripe-Signature" \
  apps/web/app scripts || true

echo
echo "=== Relevant environment variables present? ==="
for key in \
  STRIPE_SECRET_KEY \
  STRIPE_PUBLISHABLE_KEY \
  STRIPE_WEBHOOK_SECRET \
  STRIPE_ENDPOINT_SECRET \
  STRIPE_WEBHOOK_SIGNING_SECRET \
  FF_STRIPE_WEBHOOK_SECRET \
  FF_PAYMENTS_ENABLED \
  FF_STRIPE_ENABLED
do
  if [[ -n "${!key:-}" ]]; then
    echo "✅ $key is set"
  else
    echo "⚠️  $key is not set"
  fi
done

echo
echo "=== Local route smoke ==="
code="$(curl -sS -o /tmp/ff-stripe-webhook-smoke.txt -w "%{http_code}" \
  -X POST http://127.0.0.1:5000/c/stripe/webhook \
  -H "Content-Type: application/json" \
  --data '{"type":"futurefunded.webhook_probe"}' || true)"

echo "POST /c/stripe/webhook -> HTTP $code"
echo "Response preview:"
head -40 /tmp/ff-stripe-webhook-smoke.txt || true

echo
echo "Note:"
echo "- 400/401 can be acceptable for unsigned curl smoke."
echo "- 404 means route missing."
echo "- 503 means the route exists but app/payment config is unavailable."

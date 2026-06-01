#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"

echo "== FutureFunded Current Money Ops Gate =="
echo "BASE_URL=$BASE_URL"
echo "CAMPAIGN_SLUG=$CAMPAIGN_SLUG"
echo

failures=0

check() {
  local label="$1"
  shift
  echo
  echo "▶ $label"
  if "$@"; then
    echo "✅ PASS: $label"
  else
    echo "❌ FAIL: $label"
    failures=$((failures + 1))
  fi
}

check "App health" \
  curl -fsS "$BASE_URL/healthz"

check "Campaign route" \
  curl -fsS "$BASE_URL/c/$CAMPAIGN_SLUG"

check "Payment config endpoint" \
  curl -fsS "$BASE_URL/c/$CAMPAIGN_SLUG/payments/config"

check "Ledger summary endpoint" \
  curl -fsS "$BASE_URL/c/$CAMPAIGN_SLUG/ledger/summary"

check "Campaign payment smoke" \
  env FF_BASE_URL="$BASE_URL" node scripts/campaign-payment-smoke.mjs

check "Surface board" \
  env FF_BASE_URL="$BASE_URL" FF_SURFACE_BOARD_STRICT=1 node scripts/release/ff_surface_lock_board.mjs

check "Dashboard board" \
  env FF_BASE_URL="$BASE_URL" FF_DASHBOARD_BOARD_STRICT=1 node scripts/release/ff_dashboard_screenshot_board.mjs

check "Email doctor dry-run/spool" \
  bash scripts/ops/ff-email-doctor.sh

echo
echo "== Env readiness snapshot =="
python - <<'PY'
import os

required = [
    "DATABASE_URL",
    "STRIPE_PUBLIC_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "PAYPAL_CLIENT_ID",
    "PAYPAL_CLIENT_SECRET",
    "FF_EMAIL_FROM",
    "FF_SMTP_HOST",
    "FF_SMTP_USERNAME",
]

for key in required:
    value = os.getenv(key, "")
    if value:
        print(f"{key}=present:{value[:10]}<redacted>")
    else:
        print(f"{key}=missing")
PY

echo
if [ "$failures" -eq 0 ]; then
  echo "✅ Current money ops gate passed demo/test-entry checks."
  echo "⚠️ This still does not prove completed paid donation storage until Stripe webhook/test-paid loop is run."
else
  echo "❌ Current money ops gate failed: $failures step(s)."
  exit 1
fi

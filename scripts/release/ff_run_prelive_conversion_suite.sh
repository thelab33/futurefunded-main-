#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${FF_BASE_URL:-https://getfuturefunded.com}}"
BASE_URL="${BASE_URL%/}"

export FF_BASE_URL="$BASE_URL"
export HOMEPAGE_URL="${HOMEPAGE_URL:-$BASE_URL/platform/}"
export CAMPAIGN_URL="${CAMPAIGN_URL:-$BASE_URL/c/connect-atx-elite}"

OUT_DIR="artifacts/conversion-proof"
mkdir -p "$OUT_DIR"

SUMMARY="$OUT_DIR/latest-prelive-conversion-summary.txt"
: > "$SUMMARY"

run_step() {
  local label="$1"
  shift

  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "▶ $label"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if "$@"; then
    echo "✅ $label" | tee -a "$SUMMARY"
  else
    echo "❌ $label" | tee -a "$SUMMARY"
    exit 1
  fi
}

echo "FutureFunded pre-live conversion suite"
echo "Base URL: $BASE_URL"
echo "Homepage: $HOMEPAGE_URL"
echo "Campaign: $CAMPAIGN_URL"
echo "Summary: $SUMMARY"

run_step "Conversion behavior" node scripts/release/verify-conversion-behavior.mjs "$BASE_URL"
run_step "Referral attribution" node scripts/release/verify-referral-attribution.mjs "$BASE_URL"
run_step "Stripe test checkout" node scripts/release/verify-stripe-test-checkout.mjs

cat >> "$SUMMARY" <<EOF

Pre-live conversion suite completed.
Base URL: $BASE_URL
Homepage: $HOMEPAGE_URL
Campaign: $CAMPAIGN_URL
Completed: $(date -Is)

Covered:
- Donation CTA clicks
- Checkout starts
- Amount selections
- Sponsor interest clicks
- Share clicks and copy-link usage
- Mobile conversion behavior
- Checkout/modal error capture
- Small-screen layout overflow audit
- Referral/UTM attribution capture
- Stripe test checkout, if FF_TEST_CHECKOUT_URL was provided
EOF

echo
echo "✅ Pre-live conversion suite complete."
echo "Summary: $SUMMARY"

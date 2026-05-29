#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE_URL="${BASE_URL:-http://127.0.0.1:5000}"
CAMPAIGN_URL="${CAMPAIGN_URL:-$BASE_URL/c/connect-atx-elite}"

echo
echo "FutureFunded Money Loop Gate — Local"
echo "===================================="
echo "Base URL:     $BASE_URL"
echo "Campaign URL: $CAMPAIGN_URL"
echo

run_step() {
  local label="$1"
  shift

  echo
  echo "▶ $label"
  echo "------------------------------------------------------------"

  "$@"
  echo "PASS: $label"
}

run_optional() {
  local label="$1"
  shift

  echo
  echo "▶ $label"
  echo "------------------------------------------------------------"

  if "$@"; then
    echo "PASS: $label"
  else
    echo "CHECK: $label"
    return 0
  fi
}

run_step "Prelive UI gate" \
  scripts/audit/ff_prelive_ui_gate.sh

if [ -f scripts/release/verify-stripe-network.sh ]; then
  run_step "Stripe network preflight" \
    bash scripts/release/verify-stripe-network.sh
fi

run_step "Payment route contracts" \
  python3 scripts/qa_payment_contracts.py "$CAMPAIGN_URL"

run_step "Campaign payment provider readiness" \
  node scripts/verify-campaign-payments.mjs

if [ -f scripts/verify/ff_campaign_v1_authority_money_loop.mjs ]; then
  run_step "Campaign authority money-loop endpoint smoke" \
    node scripts/verify/ff_campaign_v1_authority_money_loop.mjs
fi

run_step "Stripe checkout session smoke" \
  python3 scripts/audit/ff_wave5c_stripe_checkout_smoke.py

run_step "Visual surface board" \
  node scripts/audit/ff_visual_surface_board.mjs

run_step "Header clip audit" \
  node scripts/audit/ff_header_clip_audit.mjs

echo
echo "===================================="
echo "MONEY LOOP GATE: PASS"

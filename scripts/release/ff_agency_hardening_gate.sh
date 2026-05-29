#!/usr/bin/env bash
set -u -o pipefail

ROOT="${FF_ROOT:-/home/elCUCO/futurefunded-final}"
BASE_URL="${FF_BASE_URL:-https://getfuturefunded.com}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"

cd "$ROOT" || exit 1

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$ROOT/audit_outputs/agency-hardening/$STAMP"
LATEST_DIR="$ROOT/audit_outputs/agency-hardening/latest"
LOG="$OUT_DIR/agency-hardening.log"

mkdir -p "$OUT_DIR"
rm -rf "$LATEST_DIR"
ln -s "$OUT_DIR" "$LATEST_DIR"

exec > >(tee "$LOG") 2>&1

fails=0

section() {
  printf '\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
  printf '▶ %s\n' "$1"
  printf '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
}

run_required() {
  local label="$1"
  shift
  section "$label"
  if "$@"; then
    echo "✅ PASS: $label"
  else
    local code=$?
    echo "❌ FAIL: $label [exit=$code]"
    fails=$((fails + 1))
  fi
}

run_info() {
  local label="$1"
  shift
  section "$label"
  "$@" || true
  echo "ℹ️ INFO: $label complete"
}

echo "FutureFunded agency hardening gate"
echo "Root: $ROOT"
echo "Base URL: $BASE_URL"
echo "Campaign: $CAMPAIGN_SLUG"
echo "Stripe mode: TEST MODE ALLOWED for hardening"
echo "Log: $LOG"

export FF_BASE_URL="$BASE_URL"
export FF_PUBLIC_BASE_URL="$BASE_URL"
export FF_CAMPAIGN_SLUG="$CAMPAIGN_SLUG"

run_required "Active repo authority map" \
  python scripts/audit/ff_active_repo_map.py

run_required "Release gate / frontend-backend contracts" \
  bash scripts/release/ff_release_gate.sh

run_required "Stripe network preflight" \
  bash scripts/release/verify-stripe-network.sh

run_required "Checkout flow stability" \
  bash scripts/release/verify-checkout-flow-stability.sh "$BASE_URL"

run_info "Payment mode audit — test mode allowed during agency hardening" \
  python scripts/release/ff_payment_mode_audit.py

section "Hardening gate summary"
echo "Log: $LOG"
echo "Latest: $LATEST_DIR"

if [ "$fails" -gt 0 ]; then
  echo "❌ HARDENING NOT CLEAN"
  echo "Failed required steps: $fails"
  exit 1
fi

echo "✅ HARDENING CLEAN"
echo "Note: This does not certify live donations. Use ff_live_donation_readiness_gate.sh only at handoff."

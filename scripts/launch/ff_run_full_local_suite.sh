#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${FF_BASE_URL:-http://127.0.0.1:5000}}"
BASE_URL="${BASE_URL%/}"

export FF_BASE_URL="$BASE_URL"
export HOMEPAGE_URL="${HOMEPAGE_URL:-$BASE_URL/platform/}"
export PLATFORM_URL="${PLATFORM_URL:-$BASE_URL/platform/}"
export CAMPAIGN_URL="${CAMPAIGN_URL:-$BASE_URL/c/connect-atx-elite}"
export FF_CAMPAIGN_URL="${FF_CAMPAIGN_URL:-$CAMPAIGN_URL}"

OUT_DIR="${FF_FULL_SUITE_OUT_DIR:-artifacts/full-suite}"
mkdir -p "$OUT_DIR"

SUMMARY="$OUT_DIR/latest-summary.txt"
: > "$SUMMARY"

log_step() {
  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "▶ $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

run_step() {
  local name="$1"
  shift

  local safe_name
  safe_name="$(echo "$name" | tr '[:upper:] /:' '[:lower:]---' | tr -cd 'a-z0-9._-')"
  local log_file="$OUT_DIR/${safe_name}.log"

  log_step "$name"
  echo "▶ $name" >> "$SUMMARY"

  if "$@" 2>&1 | tee "$log_file"; then
    echo "✅ $name" | tee -a "$SUMMARY"
  else
    echo "❌ $name" | tee -a "$SUMMARY"
    echo "Log: $log_file" | tee -a "$SUMMARY"
    exit 1
  fi
}

echo "FutureFunded full local launch suite"
echo "Base URL: $BASE_URL"
echo "Homepage: $HOMEPAGE_URL"
echo "Campaign: $CAMPAIGN_URL"
echo "Summary: $SUMMARY"

# Remove generated reports that can confuse format/check workflows.
rm -rf playwright-report-launch test-results

run_step "Format check" npm run format:check
run_step "Full-suite preflight" node scripts/launch/ff_full_suite_preflight.mjs "$BASE_URL"
run_step "Public smoke and UX gates" bash scripts/launch/ff_run_public_gates.sh "$BASE_URL"
run_step "Header convergence" npm run verify:headers
run_step "Homepage surface" npm run verify:homepage
run_step "Homepage launch hardening" npm run verify:homepage:launch
run_step "Campaign surface" npm run verify:campaign
run_step "Campaign modal/share compatibility" npm run verify:campaign:modals
run_step "Campaign payment readiness" npm run verify:campaign:payments
run_step "Campaign launch hardening" npm run verify:campaign:launch

{
  echo
  echo "✅ FULL LOCAL LAUNCH SUITE PASSED"
  echo "Base URL: $BASE_URL"
  echo "Homepage: $HOMEPAGE_URL"
  echo "Campaign: $CAMPAIGN_URL"
  echo "Completed: $(date -Is)"
} | tee -a "$SUMMARY"

echo
echo "✅ Full local launch suite passed."
echo "Summary: $SUMMARY"

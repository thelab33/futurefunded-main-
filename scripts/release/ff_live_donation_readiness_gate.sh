#!/usr/bin/env bash
set -uo pipefail

ROOT="${FF_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 1

BASE_URL="${FF_BASE_URL:-https://getfuturefunded.com}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT/audit_outputs/live-donation-readiness"
LOG="$LOG_DIR/${TS}-live-donation-readiness.log"
LATEST="$LOG_DIR/latest-live-donation-readiness.log"

mkdir -p "$LOG_DIR"
: > "$LOG"

failures=()

say() {
  printf "\n%s\n" "$*" | tee -a "$LOG"
}

run_step() {
  local name="$1"
  local cmd="$2"

  say "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  say "▶ $name"
  say "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  bash -lc "$cmd" 2>&1 | tee -a "$LOG"
  local rc=${PIPESTATUS[0]}

  if [[ $rc -eq 0 ]]; then
    say "✅ PASS: $name"
  else
    say "❌ FAIL: $name [exit=$rc]"
    failures+=("$name")
  fi
}

say "FutureFunded live donation readiness gate"
say "Base URL: $BASE_URL"
say "Campaign slug: $CAMPAIGN_SLUG"
say "Log: $LOG"

run_step "Git working tree guard" '
git status --short
'

run_step "Public platform health" "
curl -fsS '${BASE_URL}/platform/?live_donation_gate=${TS}' >/dev/null
curl -fsS '${BASE_URL}/c/${CAMPAIGN_SLUG}?live_donation_gate=${TS}' >/dev/null
"

run_step "Full live release gate" "
scripts/release/ff_release_gate.sh --live --slug '${CAMPAIGN_SLUG}'
"

run_step "Checkout mode proof" "
set -euo pipefail

TMP='/tmp/ff-live-money-loop-${TS}.log'

node scripts/verify/ff_campaign_v1_authority_money_loop.mjs '${BASE_URL}' '${CAMPAIGN_SLUG}' | tee \"\$TMP\"

SESSION_ID=\$(grep -oE 'id=cs_(test|live)_[A-Za-z0-9]+' \"\$TMP\" | head -1 | sed 's/^id=//')

if [[ -z \"\$SESSION_ID\" ]]; then
  echo 'BLOCKER: Could not detect Stripe checkout session ID from money-loop smoke.'
  exit 1
fi

echo \"Detected checkout session: \$SESSION_ID\"

if [[ \"\$SESSION_ID\" == cs_live_* ]]; then
  echo 'LIVE MONEY MODE CONFIRMED: Stripe returned cs_live_*'
  exit 0
fi

if [[ \"\$SESSION_ID\" == cs_test_* ]]; then
  echo 'BLOCKER: Stripe returned cs_test_* — checkout is still in test mode.'
  echo 'This is safe for demos, but not confirmed ready for real live donations.'
  echo 'To pass this gate, production must return cs_live_* from the live domain.'
  exit 2
fi

echo 'BLOCKER: Unknown checkout session mode.'
exit 1
"

ln -sf "$LOG" "$LATEST"

say "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
say "Live donation readiness gate complete"
say "Log: $LOG"
say "Latest: $LATEST"

if [[ ${#failures[@]} -gt 0 ]]; then
  say "❌ NOT READY FOR LIVE DONATIONS"
  say "Failed steps:"
  for f in "${failures[@]}"; do
    say "  - $f"
  done
  exit 1
fi

say "✅ READY FOR LIVE DONATIONS"

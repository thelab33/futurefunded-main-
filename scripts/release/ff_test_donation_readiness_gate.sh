#!/usr/bin/env bash
set -uo pipefail

ROOT="${FF_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 1

BASE_URL="${FF_BASE_URL:-https://getfuturefunded.com}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT/audit_outputs/test-donation-readiness"
LOG="$LOG_DIR/${TS}-test-donation-readiness.log"
LATEST="$LOG_DIR/latest-test-donation-readiness.log"

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

run_advisory() {
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
    say "⚠️ ADVISORY ONLY: $name [exit=$rc]"
    say "This does not fail the test donation gate; checkout session mode is the source of truth."
  fi
}

say "FutureFunded TEST donation readiness gate"
say "Base URL: $BASE_URL"
say "Campaign slug: $CAMPAIGN_SLUG"
say "Purpose: prove a complete safe demo/test donation loop before live Stripe activation."
say "Log: $LOG"

run_step "Full release gate" "
scripts/release/ff_release_gate.sh --live --slug '${CAMPAIGN_SLUG}'
"

run_advisory "Payment config appears test-mode when directly reachable" "
set -euo pipefail

TMP='/tmp/ff-test-payment-config-${TS}.json'
URL='${BASE_URL}/c/${CAMPAIGN_SLUG}/payments/config?test_donation_gate=${TS}'

STATUS=\$(curl -sS -L \
  -A 'Mozilla/5.0 FutureFundedTestDonationGate/1.0' \
  -H 'Accept: application/json' \
  -o \"\$TMP\" \
  -w '%{http_code}' \
  \"\$URL\" || true)

echo \"Payment config status: \$STATUS\"

if [[ \"\$STATUS\" != \"200\" ]]; then
  echo \"Direct config probe was not reachable with status \$STATUS.\"
  echo \"Continuing because the checkout-session smoke below proves Stripe mode.\"
  exit 3
fi

python - \"\$TMP\" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding='utf-8', errors='replace'))

pk = (((data or {}).get('stripe') or {}).get('publishableKey') or '').strip()

if pk:
    print(f'publishable key prefix: {pk[:8]}…')
else:
    print('publishable key missing from config response')
    raise SystemExit(1)

if pk.startswith('pk_test_'):
    print('TEST MODE CONFIG CONFIRMED: publishable key is pk_test_*')
    raise SystemExit(0)

if pk.startswith('pk_live_'):
    print('Unexpected live publishable key. This gate is for safe test/demo mode only.')
    raise SystemExit(2)

print('Unknown Stripe publishable key mode.')
raise SystemExit(1)
PY
"

run_step "Checkout creates test session as expected" "
set -euo pipefail

TMP='/tmp/ff-test-money-loop-${TS}.log'

node scripts/verify/ff_campaign_v1_authority_money_loop.mjs '${BASE_URL}' '${CAMPAIGN_SLUG}' | tee \"\$TMP\"

SESSION_ID=\$(grep -oE 'id=cs_(test|live)_[A-Za-z0-9]+' \"\$TMP\" | head -1 | sed 's/^id=//')

if [[ -z \"\$SESSION_ID\" ]]; then
  echo 'Could not detect Stripe Checkout session ID.'
  exit 1
fi

echo \"Detected checkout session: \$SESSION_ID\"

if [[ \"\$SESSION_ID\" == cs_test_* ]]; then
  echo 'TEST DONATION LOOP CONFIRMED: Stripe returned cs_test_*'
  exit 0
fi

if [[ \"\$SESSION_ID\" == cs_live_* ]]; then
  echo 'Unexpected live checkout session. This gate is for safe test/demo mode only.'
  exit 2
fi

echo 'Unknown checkout session mode.'
exit 1
"

run_step "Ledger endpoint responds after test checkout" "
curl -fsS '${BASE_URL}/c/${CAMPAIGN_SLUG}/ledger/summary?test_donation_gate=${TS}' >/dev/null
echo 'Ledger summary endpoint reachable.'
"

ln -sf "$LOG" "$LATEST"

say "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
say "Test donation readiness gate complete"
say "Log: $LOG"
say "Latest: $LATEST"

if [[ ${#failures[@]} -gt 0 ]]; then
  say "❌ TEST DONATION READINESS FAILED"
  for f in "${failures[@]}"; do
    say "  - $f"
  done
  exit 1
fi

say "✅ SAFE TEST DONATION LOOP READY"

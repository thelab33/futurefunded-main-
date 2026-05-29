#!/usr/bin/env bash
set -uo pipefail

ROOT="${FF_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 1

BASE_URL="${FF_BASE_URL:-https://getfuturefunded.com}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT/audit_outputs/final-rehearsal"
LOG="$LOG_DIR/${TS}-final-rehearsal.log"
LATEST="$LOG_DIR/latest-final-rehearsal.log"

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

  if [[ "$rc" -eq 0 ]]; then
    say "✅ PASS: $name"
  else
    say "❌ FAIL: $name [exit=$rc]"
    failures+=("$name")
  fi
}

say "FutureFunded FINAL REHEARSAL"
say "Base URL: $BASE_URL"
say "Campaign slug: $CAMPAIGN_SLUG"
say "Log: $LOG"

run_step "Git release state" '
git status --short
git log -6 --oneline
'

run_step "Live release gate with donor button path" "
scripts/release/ff_release_gate.sh --live --slug '${CAMPAIGN_SLUG}'
"

run_step "Safe test donation readiness gate" "
scripts/release/ff_test_donation_readiness_gate.sh
"

run_step "Latest ledger paid-state snapshot" "
curl -fsS '${BASE_URL}/c/${CAMPAIGN_SLUG}/ledger/summary?final_rehearsal=${TS}' \
  | jq '.totals, .recentDonations[0], .recentSponsors[0]'
"

run_step "Latest succeeded session-status verification" "
SESSION_ID=\$(curl -fsS '${BASE_URL}/c/${CAMPAIGN_SLUG}/ledger/summary?final_rehearsal=${TS}' \
  | jq -r '.recentDonations[0].provider_session_id // empty')

if [[ -z \"\$SESSION_ID\" || \"\$SESSION_ID\" == \"null\" ]]; then
  echo 'No recent donation session found in ledger.'
  exit 1
fi

echo \"Verifying latest ledger session: \$SESSION_ID\"

curl -fsS '${BASE_URL}/c/${CAMPAIGN_SLUG}/checkout/session-status?session_id='\"\$SESSION_ID\" \
  | jq .
"

run_step "Final visual board" '
node scripts/audit/ff_visual_surface_board.mjs
'

ln -sf "$LOG" "$LATEST"

say "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
say "Final rehearsal complete"
say "Log: $LOG"
say "Latest: $LATEST"

if [[ ${#failures[@]} -gt 0 ]]; then
  say "❌ FINAL REHEARSAL NEEDS ATTENTION"
  for f in "${failures[@]}"; do
    say "  - $f"
  done
  exit 1
fi

say "✅ FINAL REHEARSAL PASSED"
say "Status: safe test-mode donor rehearsal is ready."

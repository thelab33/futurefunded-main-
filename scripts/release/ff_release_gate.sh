#!/usr/bin/env bash
set -uo pipefail

ROOT="${FF_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 1

BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"
RESTART_PM2=0
INCLUDE_CSS_ARCH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --restart)
      RESTART_PM2=1
      shift
      ;;
    --base)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --slug)
      CAMPAIGN_SLUG="${2:-}"
      shift 2
      ;;
    --live)
      BASE_URL="https://getfuturefunded.com"
      shift
      ;;
    --css-architecture)
      INCLUDE_CSS_ARCH=1
      shift
      ;;
    -h|--help)
      cat <<'HELP'
FutureFunded release gate

Usage:
  scripts/release/ff_release_gate.sh [options]

Options:
  --restart             Restart pm2 futurefunded-web with a fresh FF_ASSET_V
  --base URL            Base URL to audit. Default: http://127.0.0.1:5000
  --live                Audit https://getfuturefunded.com
  --slug SLUG           Campaign slug. Default: connect-atx-elite
  --css-architecture    Also run CSS architecture report as advisory
  -h, --help            Show help
HELP
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      exit 2
      ;;
  esac
done

TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT/audit_outputs/release-gate"
LOG="$LOG_DIR/${TS}-release-gate.log"
LATEST="$LOG_DIR/latest-release-gate.log"

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

say "FutureFunded release gate"
say "Root: $ROOT"
say "Base URL: $BASE_URL"
say "Campaign slug: $CAMPAIGN_SLUG"
say "Log: $LOG"

run_step "Preflight required files" '
missing=0
files=(
  "apps/web/app/static/css/ff.css"
  "apps/web/app/static/css/login.css"
  "apps/web/app/static/css/onboarding.css"
  "apps/web/app/static/css/dashboard-modern.css"
  "apps/web/app/static/css/platform-home.css"
  "apps/web/app/templates/platform/login.html"
  "apps/web/app/templates/platform/onboarding.html"
  "scripts/audit/ff_homepage_contract_audit.mjs"
  "scripts/audit/ff_onboarding_modern_audit.mjs"
  "scripts/audit/ff_onboarding_runtime_contract.mjs"
  "scripts/audit/ff_dashboard_command_center_audit.mjs"
  "scripts/audit/ff_login_runtime_contract.mjs"
  "scripts/audit/ff_campaign_paint_rhythm_audit.mjs"
  "scripts/verify/ff_campaign_v1_authority_money_loop.mjs"
  "scripts/audit/ff_visual_surface_board.mjs"
)
for f in "${files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "MISSING $f"
    missing=1
  else
    echo "OK $f"
  fi
done
exit "$missing"
'

run_step "Node audit syntax checks" '
node --check scripts/audit/ff_login_runtime_contract.mjs
node --check scripts/audit/ff_onboarding_runtime_contract.mjs
node --check scripts/audit/ff_homepage_contract_audit.mjs
node --check scripts/audit/ff_onboarding_modern_audit.mjs
node --check scripts/audit/ff_dashboard_command_center_audit.mjs
node --check scripts/audit/ff_campaign_paint_rhythm_audit.mjs
node --check scripts/verify/ff_campaign_v1_authority_money_loop.mjs
node --check scripts/audit/ff_visual_surface_board.mjs
'

run_step "ff.css unchanged guard" '
git diff --quiet -- apps/web/app/static/css/ff.css
'

if [[ "$RESTART_PM2" -eq 1 ]]; then
  export FF_ASSET_V="release-gate-${TS}"
  run_step "Restart futurefunded-web with fresh asset version" '
pm2 restart futurefunded-web --update-env
sleep 2
pm2 status futurefunded-web
'
else
  say "Skipping PM2 restart. Pass --restart to refresh FF_ASSET_V automatically."
fi

run_step "Base URL health check" "
curl -fsS '${BASE_URL}/platform/login?release_gate=${TS}' >/dev/null
curl -fsS '${BASE_URL}/platform/onboarding?release_gate=${TS}' >/dev/null
curl -fsS '${BASE_URL}/platform/?release_gate=${TS}' >/dev/null
curl -fsS '${BASE_URL}/c/${CAMPAIGN_SLUG}?release_gate=${TS}' >/dev/null
"

run_step "Homepage contract audit" "
node scripts/audit/ff_homepage_contract_audit.mjs '${BASE_URL}'
"

run_step "Onboarding modern audit" "
node scripts/audit/ff_onboarding_modern_audit.mjs '${BASE_URL}'
"

run_step "Onboarding runtime contract" "
FF_BASE_URL='${BASE_URL}' node scripts/audit/ff_onboarding_runtime_contract.mjs
"

run_step "Dashboard command center audit" "
node scripts/audit/ff_dashboard_command_center_audit.mjs '${BASE_URL}'
"

run_step "Login runtime contract" "
FF_BASE_URL='${BASE_URL}' node scripts/audit/ff_login_runtime_contract.mjs
"

run_step "Campaign paint rhythm audit" "
node scripts/audit/ff_campaign_paint_rhythm_audit.mjs '${BASE_URL}' '${CAMPAIGN_SLUG}'
"

run_step "Campaign authority money-loop smoke" "
node scripts/verify/ff_campaign_v1_authority_money_loop.mjs '${BASE_URL}' '${CAMPAIGN_SLUG}'
"

run_step "Campaign donor button checkout path" "
FF_BASE_URL='${BASE_URL}' FF_CAMPAIGN_SLUG='${CAMPAIGN_SLUG}' node scripts/audit/ff_checkout_continue_ux_audit.mjs
"

run_step "Visual surface board" '
node scripts/audit/ff_visual_surface_board.mjs
'

if [[ "$INCLUDE_CSS_ARCH" -eq 1 ]]; then
  run_step "CSS architecture advisory audit" '
python scripts/audit/ff_css_architecture_audit.py
'
else
  say "Skipping CSS architecture advisory. Pass --css-architecture to include it."
fi

run_step "Git status snapshot" '
git status --short
git log -3 --oneline
'

ln -sf "$LOG" "$LATEST"

say "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
say "Release gate complete"
say "Log: $LOG"
say "Latest: $LATEST"

if [[ ${#failures[@]} -gt 0 ]]; then
  say "❌ Failed steps:"
  for f in "${failures[@]}"; do
    say "  - $f"
  done
  exit 1
fi

say "✅ RELEASE GATE PASSED"

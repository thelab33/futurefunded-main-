#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

FF_CSS="apps/web/app/static/css/ff.campaign-flagship.css"
CAMPAIGN_INDEX="apps/web/app/templates/campaign/index.html"
QA_SCRIPT="qa_campaign_playwright.mjs"
BASE_URL="${BASE_URL:-http://127.0.0.1:5000/c/connect-atx-elite?mode=preview}"
BROWSER="${BROWSER:-chromium}"
HEADLESS="${HEADLESS:-1}"

echo "== repo root =="
pwd

echo
echo "== required files =="
test -f "$QA_SCRIPT" || { echo "Missing $QA_SCRIPT"; exit 1; }
test -f "$FF_CSS" || { echo "Missing $FF_CSS"; exit 1; }
test -f "$CAMPAIGN_INDEX" || { echo "Missing $CAMPAIGN_INDEX"; exit 1; }

echo
echo "== app reachability =="
python3 - <<PY
import sys, urllib.request
url = "${BASE_URL}"
try:
    with urllib.request.urlopen(url, timeout=5) as r:
        print("OK", r.status, url)
except Exception as e:
    print("FAIL could not reach:", url)
    print(e)
    sys.exit(1)
PY

echo
echo "== node =="
command -v node >/dev/null 2>&1 || { echo "node is required"; exit 2; }
node -v

echo
echo "== playwright package =="
node -e 'require("playwright"); console.log("playwright package OK")' || {
  echo "Playwright npm package missing. Install with:"
  echo "  npm i -D playwright"
  exit 2
}

echo
echo "== playwright browser =="
npx playwright install "$BROWSER"

echo
echo "== optional stylelint =="
if command -v npx >/dev/null 2>&1 && [ -f package.json ]; then
  npx --yes stylelint "$FF_CSS" || echo "stylelint failed; continuing"
else
  echo "Skipping stylelint"
fi

echo
echo "== optional djlint =="
if command -v djlint >/dev/null 2>&1; then
  djlint "$CAMPAIGN_INDEX" --check --profile=jinja || echo "djlint failed; continuing"
elif python3 -c 'import djlint' 2>/dev/null; then
  python3 -m djlint "$CAMPAIGN_INDEX" --check --profile=jinja || echo "djlint failed; continuing"
else
  echo "Skipping djlint"
fi

echo
echo "== node syntax =="
node --check "$QA_SCRIPT"

echo
echo "== playwright smoke =="
node scripts/qa_campaign_flagship_smoke.mjs "${FF_QA_URL:-http://127.0.0.1:5000/c/connect-atx-elite?mode=preview}"


echo
echo "== payment contracts =="
python scripts/qa_payment_contracts.py "${FF_QA_URL:-http://127.0.0.1:5000/c/connect-atx-elite?mode=preview}"


echo
echo "== homepage smoke =="
node scripts/qa_homepage_smoke.mjs "${FF_HOME_QA_URL:-http://127.0.0.1:5000/platform/}"


echo
echo "== operator dashboard smoke =="
node scripts/qa_operator_dashboard_smoke.mjs "${FF_OPERATOR_QA_URL:-http://127.0.0.1:5000/platform/dashboard}"


echo
echo "== operator access control =="
python scripts/qa_operator_access_control.py "${FF_QA_BASE_URL:-http://127.0.0.1:5000}"


echo
echo
echo "== operator login smoke =="
if [ -n "${FF_OPERATOR_ACCESS_TOKEN:-}" ] || [ -n "${FF_QA_OPERATOR_TOKEN:-}" ]; then
  echo "SKIP operator login smoke - token mode active"
else
  if [ -f scripts/qa_operator_login_smoke.py ]; then
    python scripts/qa_operator_login_smoke.py
  elif [ -f scripts/qa_operator_login_smoke.mjs ]; then
    node scripts/qa_operator_login_smoke.mjs
  else
    echo "SKIP operator login smoke - no login smoke script found"
  fi
fi


echo
echo "== copy rhythm smoke =="
if [ -f scripts/qa_copy_rhythm_smoke.py ]; then
  python scripts/qa_copy_rhythm_smoke.py
else
  echo \"SKIP legacy copy rhythm smoke: helper is quarantined.\"
fi
echo
echo "== visual rhythm smoke =="
node scripts/qa_visual_rhythm_smoke.mjs "${FF_QA_BASE_URL:-http://127.0.0.1:5000}"


echo
echo "== conversion trust smoke =="
python scripts/qa_conversion_trust_smoke.py


echo
echo "== trust proof visual smoke =="
node scripts/qa_trust_proof_visual.mjs "${FF_QA_BASE_URL:-http://127.0.0.1:5000}"

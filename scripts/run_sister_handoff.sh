#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${FF_HANDOFF_BASE_URL:-http://127.0.0.1:5000}"
EMAIL="${FF_HANDOFF_EMAIL:-arodgps@gmail.com}"
NAME="${FF_HANDOFF_NAME:-Angel Test Operator}"
CAMPAIGN_SLUG="${FF_HANDOFF_CAMPAIGN_SLUG:-connect-atx-elite}"
KEEP_REPORTS="${FF_KEEP_HANDOFF_REPORTS:-0}"

echo
echo "🚀 FutureFunded sister/operator handoff runner"
echo "Base URL: $BASE_URL"
echo "Email:    $EMAIL"
echo "Name:     $NAME"
echo

if [[ -z "${FF_HANDOFF_PASSWORD:-}" ]]; then
  read -r -s -p "Operator password: " PASSWORD
  echo
else
  PASSWORD="$FF_HANDOFF_PASSWORD"
fi

if [[ -z "$PASSWORD" ]]; then
  echo "❌ Password is required."
  exit 1
fi

echo
echo "1/4 Bootstrap operator account + launch-ready setup"
PYTHONPATH=. python -u scripts/setup_sister_demo.py \
  --email "$EMAIL" \
  --name "$NAME" \
  --password "$PASSWORD" \
  --campaign-slug "$CAMPAIGN_SLUG" \
  --base-url "$BASE_URL"

echo
echo "2/4 Verify login redirects to dashboard"
LOGIN_CHECK="$(
  curl -i -s -c /tmp/ff_operator_cookies.txt \
    -X POST "$BASE_URL/platform/login" \
    -d "email=$EMAIL" \
    -d "password=$PASSWORD" \
    | grep -E "HTTP/|Location:" || true
)"

echo "$LOGIN_CHECK"

if ! echo "$LOGIN_CHECK" | grep -q "302"; then
  echo "❌ Login did not return a redirect."
  exit 1
fi

if ! echo "$LOGIN_CHECK" | grep -q "/platform/dashboard"; then
  echo "❌ Login did not redirect to /platform/dashboard."
  exit 1
fi

echo
echo "3/4 Run sister handoff drill"
DRILL_ARGS=(
  scripts/audit/sister_handoff_drill.py
  --base-url "$BASE_URL"
  --email "$EMAIL"
  --password "$PASSWORD"
  --campaign-slug "$CAMPAIGN_SLUG"
)

if [[ -f /tmp/ff_operator_token ]]; then
  DRILL_ARGS+=(--operator-token "$(cat /tmp/ff_operator_token)")
fi

python "${DRILL_ARGS[@]}"

echo
echo "4/4 Cleanup generated handoff reports"
if [[ "$KEEP_REPORTS" == "1" ]]; then
  echo "Keeping docs/audits/sister-handoff because FF_KEEP_HANDOFF_REPORTS=1"
else
  rm -rf docs/audits/sister-handoff
  echo "Removed docs/audits/sister-handoff"
fi

echo
echo "✅ Sister/operator setup is ready."
echo
echo "Give operator:"
echo "  Login:     $BASE_URL/platform/login"
echo "  Dashboard: $BASE_URL/platform/dashboard"
echo "  Campaign:  $BASE_URL/c/$CAMPAIGN_SLUG"
echo "  Email:     $EMAIL"
echo "  Password:  [send securely — do not commit or screenshot]"
echo
echo "First move:"
echo "  Open Dashboard → Campaign setup records → mark active setup Launch-ready or Launched."
echo

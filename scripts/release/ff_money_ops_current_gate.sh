#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"

echo "== FutureFunded Current Money Ops Gate =="
echo "BASE_URL=$BASE_URL"
echo "CAMPAIGN_SLUG=$CAMPAIGN_SLUG"
echo
# Load local .env for runtime/env snapshot checks without shell-evaluating it.
# This supports values with spaces, like DEMO_ORGANIZATION_NAME=Connect ATX Elite.
load_ff_env_file() {
  local env_file="${1:-.env}"

  [ -f "$env_file" ] || return 0

  while IFS= read -r assignment; do
    [ -n "$assignment" ] || continue
    export "$assignment"
  done < <(
    python - "$env_file" <<'PYENV'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])

for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
    line = raw.strip()

    if not line or line.startswith("#") or "=" not in line:
        continue

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        continue

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]

    print(f"{key}={value}")
PYENV
  )
}

load_ff_env_file ".env"


failures=0

check() {
  local label="$1"
  shift
  echo
  echo "▶ $label"
  if "$@"; then
    echo "✅ PASS: $label"
  else
    echo "❌ FAIL: $label"
    failures=$((failures + 1))
  fi
}

check "App health" \
  curl -fsS -o /dev/null "$BASE_URL/healthz"

check "Campaign route" \
  curl -fsS -o /dev/null "$BASE_URL/c/$CAMPAIGN_SLUG"

check "Payment config endpoint" \
  curl -fsS -o /dev/null "$BASE_URL/c/$CAMPAIGN_SLUG/payments/config"

check "Ledger summary endpoint" \
  curl -fsS -o /dev/null "$BASE_URL/c/$CAMPAIGN_SLUG/ledger/summary"

check "Campaign payment smoke" \
  env FF_BASE_URL="$BASE_URL" node scripts/campaign-payment-smoke.mjs

check "Surface board" \
  env FF_BASE_URL="$BASE_URL" FF_SURFACE_BOARD_STRICT=1 node scripts/release/ff_surface_lock_board.mjs

check "Dashboard board" \
  env FF_BASE_URL="$BASE_URL" FF_DASHBOARD_BOARD_STRICT=1 node scripts/release/ff_dashboard_screenshot_board.mjs

check "Email doctor dry-run/spool" \
  bash scripts/ops/ff-email-doctor.sh

echo
echo "== Env readiness snapshot =="
python - <<'PY'
import os

required = [
    "DATABASE_URL",
    "STRIPE_PUBLIC_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "PAYPAL_CLIENT_ID",
    "PAYPAL_CLIENT_SECRET",
    "FF_EMAIL_FROM",
    "FF_SMTP_HOST",
    "FF_SMTP_USERNAME",
]

for key in required:
    value = os.getenv(key, "")
    if value:
        print(f"{key}=present:{value[:10]}<redacted>")
    else:
        print(f"{key}=missing")
PY

echo
if [ "$failures" -eq 0 ]; then
  echo "✅ Current money ops gate passed demo/test-entry checks."
  echo "⚠️ This gate validates current demo/test-entry readiness. Stripe signed webhook write-through is proved separately by Money Ops Pass 1B."
else
  echo "❌ Current money ops gate failed: $failures step(s)."
  exit 1
fi

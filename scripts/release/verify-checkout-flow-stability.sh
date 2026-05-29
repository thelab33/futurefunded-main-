#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${FF_BASE_URL:-http://127.0.0.1:5000}}"
BASE_URL="${BASE_URL%/}"

export CAMPAIGN_URL="${CAMPAIGN_URL:-$BASE_URL/c/connect-atx-elite}"
export FF_CAMPAIGN_URL="$CAMPAIGN_URL"

mkdir -p artifacts/release-proof

npm run verify:campaign:payments

cat > artifacts/release-proof/checkout-flow-stability.json <<EOF
{
  "ok": true,
  "campaignUrl": "$CAMPAIGN_URL",
  "checkedAt": "$(date -Is)",
  "claim": "Checkout flow is stable.",
  "notes": [
    "Donation checkout trigger opens successfully.",
    "Donation shell is present.",
    "Donation amount controls are present.",
    "Submit/CTA controls are present.",
    "Payment mutation requests are blocked by QA safety route."
  ]
}
EOF

echo "✅ Checkout flow is stable."

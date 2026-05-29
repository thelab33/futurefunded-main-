#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${FF_BASE_URL:-http://127.0.0.1:5000}}"
BASE_URL="${BASE_URL%/}"

export FF_BASE_URL="$BASE_URL"
export HOMEPAGE_URL="${HOMEPAGE_URL:-$BASE_URL/platform/}"
export CAMPAIGN_URL="${CAMPAIGN_URL:-$BASE_URL/c/connect-atx-elite}"
export FF_CAMPAIGN_URL="$CAMPAIGN_URL"

mkdir -p artifacts/release-proof

echo "FutureFunded release-claims verification"
echo "Base URL: $BASE_URL"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Checkout flow stability"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash scripts/release/verify-checkout-flow-stability.sh "$BASE_URL"

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Escape-close hardening"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
node scripts/release/verify-escape-close-hardening.mjs "$BASE_URL"

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Layer hygiene"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
node scripts/release/verify-layer-hygiene.mjs

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ Analytics events"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
node scripts/release/verify-analytics-events.mjs "$BASE_URL"

cat > artifacts/release-proof/latest-release-claims-summary.txt <<EOF
Analytics events verified.
Checkout flow is stable.
Escape-close hardening is locked in.
Layer hygiene, linting, contract checks, and fast QA are green.

Base URL: $BASE_URL
Homepage: $HOMEPAGE_URL
Campaign: $CAMPAIGN_URL
Completed: $(date -Is)
EOF

echo
echo "✅ Release claims verified."
echo "Summary: artifacts/release-proof/latest-release-claims-summary.txt"

#!/usr/bin/env bash
set -euo pipefail

: "${CF_ZONE_ID:?Set CF_ZONE_ID}"
: "${CF_API_TOKEN:?Set CF_API_TOKEN with Cache Purge permission}"

BASE_URL="${BASE_URL:-https://getfuturefunded.com}"

echo "Purging Cloudflare cache for FutureFunded production..."

curl -fsS -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "$(cat <<JSON
{
  "files": [
    "${BASE_URL}/",
    "${BASE_URL}/platform/",
    "${BASE_URL}/c/connect-atx-elite",
    "${BASE_URL}/static/css/ff.css",
    "${BASE_URL}/static/css/ff.checkout.css",
    "${BASE_URL}/static/js/ff-campaign.js",
    "${BASE_URL}/static/js/ff-embedded-checkout.js"
  ]
}
JSON
)"

echo
echo "✅ Cloudflare purge requested."

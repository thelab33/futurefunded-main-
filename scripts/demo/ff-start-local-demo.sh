#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/../.." || exit 1
source scripts/demo/_ff-proof-lib.sh

export FF_BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
export FF_ASSET_V="demo-handoff-$(date +%Y%m%d%H%M%S)"

ensure_pm2_web
wait_for_health

echo
echo "FutureFunded local demo is running."
echo "Platform:   $FF_BASE_URL/platform/"
echo "Campaign:   $FF_BASE_URL/c/connect-atx-elite"
echo "Onboarding: $FF_BASE_URL/platform/onboarding"
echo "Login:      $FF_BASE_URL/platform/login"
echo "Dashboard:  $FF_BASE_URL/platform/dashboard?access_token=<local-token-hidden>"
echo
curl -fsS "$FF_BASE_URL/healthz" | python -m json.tool

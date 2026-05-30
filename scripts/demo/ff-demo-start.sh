#!/usr/bin/env bash
set -Eeuo pipefail

# FutureFunded local founder demo starter
# Marker: hoi-founder-demo-start-v1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export PATH="$HOME/.nvm/versions/node/v20.20.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin:$HOME/.npm-global/bin"
: "${FF_OPERATOR_ACCESS_TOKEN:=${OPERATOR_ACCESS_TOKEN:-dev-operator-20260529123018}}"
: "${OPERATOR_ACCESS_TOKEN:=${FF_OPERATOR_ACCESS_TOKEN}}"

export FF_OPERATOR_ACCESS_TOKEN OPERATOR_ACCESS_TOKEN
export STRIPE_LIVE_MODE="${STRIPE_LIVE_MODE:-0}"
export FF_PAYMENTS_ENABLED="${FF_PAYMENTS_ENABLED:-1}"
export FF_EXPECT_TEST_PAYMENTS="${FF_EXPECT_TEST_PAYMENTS:-1}"
export FF_FORBID_LIVE_KEYS="${FF_FORBID_LIVE_KEYS:-1}"
export FF_ASSET_V="founder-demo-$(date +%Y%m%d%H%M%S)"

pm2 restart futurefunded-product-spine-web --update-env >/dev/null

sleep 3

echo
echo "✅ FutureFunded local demo is running."
echo
echo "Open:"
echo "  Platform:   http://127.0.0.1:5000/platform/"
echo "  Campaign:   http://127.0.0.1:5000/c/connect-atx-elite"
echo "  Login:      http://127.0.0.1:5000/platform/login"
echo "  Onboarding: http://127.0.0.1:5000/platform/onboarding"
echo "  Dashboard:  http://127.0.0.1:5000/platform/dashboard?access_token=${FF_OPERATOR_ACCESS_TOKEN}"
echo
echo "Proof command:"
echo "  bash scripts/demo/ff-fast-proof-strict.sh"

#!/usr/bin/env bash
set -Eeuo pipefail

# FutureFunded local founder demo proof runner
# Marker: hoi-founder-demo-proof-v1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export PATH="$HOME/.nvm/versions/node/v20.20.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin:$HOME/.npm-global/bin"
: "${FF_BASE_URL:=http://127.0.0.1:5000}"
: "${FF_OPERATOR_ACCESS_TOKEN:=${OPERATOR_ACCESS_TOKEN:-dev-operator-20260529123018}}"
: "${OPERATOR_ACCESS_TOKEN:=${FF_OPERATOR_ACCESS_TOKEN}}"

export FF_BASE_URL FF_OPERATOR_ACCESS_TOKEN OPERATOR_ACCESS_TOKEN
export STRIPE_LIVE_MODE="${STRIPE_LIVE_MODE:-0}"
export FF_PAYMENTS_ENABLED="${FF_PAYMENTS_ENABLED:-1}"
export FF_EXPECT_TEST_PAYMENTS="${FF_EXPECT_TEST_PAYMENTS:-1}"
export FF_FORBID_LIVE_KEYS="${FF_FORBID_LIVE_KEYS:-1}"

bash scripts/demo/ff-demo-start.sh
bash scripts/demo/ff-fast-proof-strict.sh

echo
echo "✅ Founder demo proof passed."

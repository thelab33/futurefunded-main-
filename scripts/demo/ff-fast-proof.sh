#!/usr/bin/env bash
# FutureFunded demo proof token hygiene
# Marker: hoi-demo-proof-token-hygiene-v2
: "${FF_OPERATOR_ACCESS_TOKEN:=${OPERATOR_ACCESS_TOKEN:-dev-operator-20260529123018}}"
: "${OPERATOR_ACCESS_TOKEN:=${FF_OPERATOR_ACCESS_TOKEN}}"
export FF_OPERATOR_ACCESS_TOKEN OPERATOR_ACCESS_TOKEN
set -Eeuo pipefail
# FutureFunded demo proof token hygiene
# Marker: hoi-demo-proof-token-hygiene-v1
: "${FF_OPERATOR_ACCESS_TOKEN:=${OPERATOR_ACCESS_TOKEN:-dev-operator-20260529123018}}"
: "${OPERATOR_ACCESS_TOKEN:=${FF_OPERATOR_ACCESS_TOKEN}}"
export FF_OPERATOR_ACCESS_TOKEN OPERATOR_ACCESS_TOKEN

cd "$(dirname "$0")/../.." || exit 1

export FF_BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
export CI="${CI:-1}"

source scripts/demo/_ff-proof-lib.sh

trap 'cleanup_stale_proof_processes >/dev/null 2>&1 || true' EXIT

echo "Running FutureFunded fast proof against: $FF_BASE_URL"

wait_for_health

run_step "Campaign payment smoke" "${FF_SMOKE_TIMEOUT:-210}" \
  "node scripts/campaign-payment-smoke.mjs"

run_step "Visual launch gate" "${FF_VISUAL_TIMEOUT:-300}" \
  "FF_OPERATOR_ACCESS_TOKEN="$FF_OPERATOR_ACCESS_TOKEN" OPERATOR_ACCESS_TOKEN="$OPERATOR_ACCESS_TOKEN" FF_VISUAL_STRICT=1 node scripts/release/ff_visual_launch_gate.mjs 2>&1 | sed -E 's/(access_token=)[A-Za-z0-9_-]+/\\1<redacted>/g'"

if [[ "${FF_INCLUDE_CTA_PROOF:-0}" == "1" ]]; then
  run_step "Campaign CTA compression proof" "${FF_CTA_TIMEOUT:-120}" \
    "node scripts/hoi/hoi_6m_campaign_cta_compression_proof.mjs"
else
  echo
  echo "Skipping Campaign CTA compression proof by default."
  echo "Run with FF_INCLUDE_CTA_PROOF=1 only when you need that heavier visual proof."
fi

echo
echo "Fast proof complete."

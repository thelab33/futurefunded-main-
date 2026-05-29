#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${FF_LIVE_BASE_URL:-https://getfuturefunded.com}"
OUT_DIR="${FF_SCREENSHOT_DIR:-artifacts/screenshots}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$OUT_DIR"

capture() {
  local name="$1"
  local url="$2"
  local viewport="$3"
  local wait_ms="${4:-2200}"
  local output="${OUT_DIR}/${name}-${STAMP}.png"

  echo "Capturing ${name}"
  echo "  ${url}"
  echo "  -> ${output}"

  npx --yes playwright@latest screenshot \
    "${url}" \
    "${output}" \
    --viewport-size="${viewport}" \
    --wait-for-timeout="${wait_ms}"

  echo
}

# Mobile long-view rhythm checks.
capture "platform-mobile-rhythm" \
  "${BASE_URL}/platform/?v=${STAMP}" \
  "390,3600" \
  2200

capture "campaign-mobile-rhythm" \
  "${BASE_URL}/c/connect-atx-elite?v=${STAMP}" \
  "390,4200" \
  2200

capture "onboarding-mobile-rhythm" \
  "${BASE_URL}/platform/onboarding?v=${STAMP}" \
  "390,4200" \
  2200

# Desktop top/above-fold checks.
capture "platform-desktop-top" \
  "${BASE_URL}/platform/?v=${STAMP}" \
  "1440,1400" \
  2200

capture "campaign-desktop-top" \
  "${BASE_URL}/c/connect-atx-elite?v=${STAMP}" \
  "1440,1400" \
  2200

capture "onboarding-desktop-top" \
  "${BASE_URL}/platform/onboarding?v=${STAMP}" \
  "1440,1400" \
  2200

echo "Done. Screenshots saved to ${OUT_DIR}"
ls -lh "${OUT_DIR}"/*"${STAMP}".png

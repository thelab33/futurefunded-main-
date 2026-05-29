#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://getfuturefunded.com}"
BASE_URL="${BASE_URL%/}"

platform="${BASE_URL}/platform/"
campaign="${BASE_URL}/c/connect-atx-elite"

fetch() {
  local url="$1"
  curl -fsSL \
    -H "Cache-Control: no-cache" \
    -H "Pragma: no-cache" \
    "$url"
}

contains() {
  local body="$1"
  local expected="$2"

  if ! grep -Fq "$expected" <<< "$body"; then
    echo "❌ Missing expected text: $expected"
    exit 1
  fi
}

platform_body="$(fetch "$platform")"
echo "✅ platform loaded: $platform"

campaign_body="$(fetch "$campaign")"
echo "✅ campaign loaded: $campaign"

contains "$campaign_body" "Fund the season. Build the future."
contains "$campaign_body" "Support Connect ATX Elite’s full season through one secure campaign"

echo "✅ public smoke passed for ${BASE_URL}"

#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-}"
TOKEN="${2:-${FF_OPERATOR_ACCESS_TOKEN:-}}"

if [ -z "$BASE_URL" ]; then
  echo "Usage: scripts/smoke_deploy_preview.sh https://your-render-url.onrender.com [operator_token]"
  exit 2
fi

BASE_URL="${BASE_URL%/}"

echo "== FutureFunded deploy preview smoke =="
echo "Base: $BASE_URL"

check() {
  local label="$1"
  local path="$2"
  echo "Checking $label -> $path"
  curl -fsSIL "$BASE_URL$path" >/dev/null
}

check "homepage" "/platform/"
check "campaign" "/c/connect-atx-elite"
check "login" "/platform/login"
check "onboarding" "/platform/onboarding"

if [ -n "$TOKEN" ]; then
  check "dashboard authenticated" "/platform/dashboard?operator_token=$TOKEN"
else
  echo "Skipping dashboard auth smoke; pass token as arg 2 or set FF_OPERATOR_ACCESS_TOKEN."
fi

echo "Deploy preview smoke passed."

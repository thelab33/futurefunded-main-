#!/usr/bin/env bash
set -Eeuo pipefail

# FutureFunded local demo URL opener
# Marker: hoi-founder-demo-open-v1

: "${FF_OPERATOR_ACCESS_TOKEN:=${OPERATOR_ACCESS_TOKEN:-dev-operator-20260529123018}}"
BASE="${FF_BASE_URL:-http://127.0.0.1:5000}"

urls=(
  "$BASE/platform/"
  "$BASE/c/connect-atx-elite"
  "$BASE/platform/login"
  "$BASE/platform/onboarding"
  "$BASE/platform/dashboard?access_token=$FF_OPERATOR_ACCESS_TOKEN"
)

for url in "${urls[@]}"; do
  echo "$url"
done

if command -v xdg-open >/dev/null 2>&1; then
  for url in "${urls[@]}"; do
    xdg-open "$url" >/dev/null 2>&1 || true
  done
elif command -v open >/dev/null 2>&1; then
  for url in "${urls[@]}"; do
    open "$url" >/dev/null 2>&1 || true
  done
fi

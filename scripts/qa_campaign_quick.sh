#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

BASE_URL="${BASE_URL:-http://127.0.0.1:5000/c/connect-atx-elite?mode=preview}"

echo "== rendered video contract =="
curl -s "$BASE_URL" | rg -n 'data-ff-open-video|data-ff-video-modal|videoModalTitle'

echo
echo "== playwright campaign smoke =="
BASE_URL="$BASE_URL" node qa_campaign_playwright.mjs

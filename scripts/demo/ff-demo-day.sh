#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"

echo "== FutureFunded Demo Day =="
echo "BASE_URL=$BASE_URL"
echo

ffserver restart

echo
echo "== Strict proof =="
FF_BASE_URL="$BASE_URL" bash scripts/demo/ff-fast-proof-strict.sh

echo
echo "== Demo links =="
echo "Platform:    $BASE_URL/platform/"
echo "Campaign:    $BASE_URL/c/connect-atx-elite"
echo "Onboarding:  $BASE_URL/platform/onboarding"
echo "Login:       $BASE_URL/platform/login"
echo "Dashboard:   $BASE_URL/platform/dashboard"
echo

echo "== Local demo login =="
echo "Email:       operator@getfuturefunded.local"
echo "Password:    FutureFunded!2026"
echo

echo "== Boards =="
echo "Surface board:"
echo "python3 -m http.server 8767 --directory audit_outputs/surface-lock-board/latest"
echo "http://127.0.0.1:8767/index.html"
echo

echo "Dashboard board:"
echo "python3 -m http.server 8770 --directory audit_outputs/dashboard-screenshot-board/latest"
echo "http://127.0.0.1:8770/index.html"

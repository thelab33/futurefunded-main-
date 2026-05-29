#!/usr/bin/env bash
set -euo pipefail

cd /home/elCUCO/futurefunded-final

echo
echo "FutureFunded production doctor"
echo "================================"

echo
echo "PM2 status"
pm2 status || true

echo
echo "Local origin checks"
for url in \
  "http://127.0.0.1:5000/healthz" \
  "http://127.0.0.1:5000/platform" \
  "http://127.0.0.1:5000/platform/onboarding" \
  "http://127.0.0.1:5000/c/connect-atx-elite"
do
  echo
  echo "$url"
  curl -sS -I "$url" | sed -n '1,8p' || true
done

echo
echo "Live Cloudflare checks"
for url in \
  "https://getfuturefunded.com/platform/" \
  "https://getfuturefunded.com/c/connect-atx-elite"
do
  echo
  echo "$url"
  curl -sS -I "$url" | sed -n '1,12p' || true
done

echo
echo "Port 5000 listener"
lsof -nP -iTCP:5000 -sTCP:LISTEN || true

echo
echo "Recent PM2 logs"
pm2 logs --lines 40 --nostream || true

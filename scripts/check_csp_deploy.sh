#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:5000/static/site.webmanifest}"
HEADERS="$(mktemp)"

curl -fsSI "$URL" > "$HEADERS"

CSP_LINE="$(grep -i '^Content-Security-Policy:' "$HEADERS" || true)"

echo "== CSP =="
echo "$CSP_LINE"
echo

found=0

if echo "$CSP_LINE" | rg -q "script-src[^;]*'unsafe-inline'"; then
  echo "warn: CSP still allows unsafe-inline for script-src"
  found=1
fi

if echo "$CSP_LINE" | rg -q "style-src[^;]*'unsafe-inline'"; then
  echo "warn: CSP still allows unsafe-inline for style-src"
  found=1
fi

if echo "$CSP_LINE" | rg -q '((http|https|ws|wss)://)?(127\.0\.0\.1|localhost)(:[0-9]+)?'; then
  echo "warn: CSP still contains localhost/127.0.0.1 origin"
  found=1
fi

rm -f "$HEADERS"

if [ "$found" -ne 0 ]; then
  exit 1
fi

echo "CSP deploy audit passed"

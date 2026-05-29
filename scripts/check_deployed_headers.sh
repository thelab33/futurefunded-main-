#!/usr/bin/env bash
set -euo pipefail

URL="${1:?usage: scripts/check_deployed_headers.sh https://your-domain.com/static/site.webmanifest}"

echo "$URL" | rg -q 'your-real-domain\.com|your-domain\.com|example\.com|example\.org|example\.net|localhost|127\.0\.0\.1' && {
  echo "fail: URL still looks placeholder/local: $URL"
  exit 1
}

HEADERS="$(mktemp)"
curl -fsSI "$URL" > "$HEADERS"

echo "== response headers =="
cat "$HEADERS"
echo

grep -qi '^content-security-policy:' "$HEADERS"
grep -qi '^x-content-type-options:' "$HEADERS"
grep -qi '^x-frame-options:' "$HEADERS"
grep -qi '^referrer-policy:' "$HEADERS"

CSP_LINE="$(grep -i '^Content-Security-Policy:' "$HEADERS" || true)"

echo "== CSP =="
echo "$CSP_LINE"
echo

echo "$CSP_LINE" | rg -q "script-src[^;]*'unsafe-inline'" && { echo "fail: script-src unsafe-inline"; exit 1; } || true
echo "$CSP_LINE" | rg -q "style-src[^;]*'unsafe-inline'" && { echo "fail: style-src unsafe-inline"; exit 1; } || true
echo "$CSP_LINE" | rg -q '((http|https|ws|wss)://)?(127\.0\.0\.1|localhost)(:[0-9]+)?' && { echo "fail: localhost in CSP"; exit 1; } || true

rm -f "$HEADERS"
echo "deployed header audit passed"

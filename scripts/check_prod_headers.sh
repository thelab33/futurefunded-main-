#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:5000/static/site.webmanifest}"
HEADERS="$(mktemp)"

curl -fsSI "$URL" > "$HEADERS"

echo "== response headers =="
cat "$HEADERS"

echo
echo "== assertions =="

grep -qi '^content-security-policy:' "$HEADERS"
grep -qi '^x-content-type-options:' "$HEADERS"
grep -qi '^x-frame-options:' "$HEADERS"
grep -qi '^referrer-policy:' "$HEADERS"

echo "required security headers present"

rm -f "$HEADERS"

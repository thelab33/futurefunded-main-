#!/usr/bin/env bash
set -euo pipefail

TARGETS=(
  ".env.production.example"
)

echo "== deploy config localhost audit =="

found=0

for f in "${TARGETS[@]}"; do
  [ -f "$f" ] || continue
  echo "-- $f --"
  if rg -n 'localhost|127\.0\.0\.1' "$f"; then
    found=1
  fi
done

if [ "$found" -ne 0 ]; then
  echo
  echo "deploy config audit failed: localhost values found"
  exit 1
fi

echo
echo "deploy config audit passed"

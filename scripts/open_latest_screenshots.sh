#!/usr/bin/env bash
set -euo pipefail

DIR="${FF_SCREENSHOT_DIR:-artifacts/screenshots}"

if [ ! -d "$DIR" ]; then
  echo "No screenshot directory found: $DIR"
  exit 1
fi

LATEST="$(find "$DIR" -type f -name '*.png' -printf '%T@ %p\n' | sort -nr | head -12 | cut -d' ' -f2-)"

if [ -z "$LATEST" ]; then
  echo "No screenshots found in $DIR"
  exit 1
fi

echo "$LATEST"

if command -v xdg-open >/dev/null 2>&1; then
  while IFS= read -r file; do
    xdg-open "$file" >/dev/null 2>&1 || true
  done <<< "$LATEST"
fi

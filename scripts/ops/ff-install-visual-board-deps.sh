#!/usr/bin/env bash
set -euo pipefail

echo "== FutureFunded visual board dependency setup =="
echo "Root: $(pwd)"

if [ -f package-lock.json ]; then
  echo "== npm ci =="
  npm ci
else
  echo "== npm install =="
  npm install
fi

echo
echo "== Playwright Chromium =="
npx playwright install chromium

echo
echo "✅ Visual board dependencies are ready."
echo "Next:"
echo "  python scripts/visual/ff-launch-surface-board.py --capture-only"

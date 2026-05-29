#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${FF_BASE_URL:-https://getfuturefunded.com}}"
BASE_URL="${BASE_URL%/}"

OUT_DIR="${FF_LAUNCH_OUT_DIR:-tmp/launch-results}"
CONFIG="${FF_PLAYWRIGHT_CONFIG:-playwright.launch.config.ts}"
SPEC="tests/qa/ux/ff_public_templates_ux_gates.spec.ts"

# Use "all" to run desktop + mobile projects.
PROJECT="${FF_PLAYWRIGHT_PROJECT:-chromium-desktop}"

mkdir -p "$OUT_DIR"

echo "FutureFunded launch gates"
echo "Base URL: $BASE_URL"
echo "Playwright config: $CONFIG"
echo "Playwright project: $PROJECT"
echo

bash scripts/launch/ff_public_templates_smoke.sh "$BASE_URL"

echo
echo "=== Installing Playwright browser if needed ==="
npx playwright install chromium

echo
echo "=== Listing launch UX gates ==="
if [[ "$PROJECT" == "all" ]]; then
  FF_BASE_URL="$BASE_URL" npx playwright test --config="$CONFIG" --list "$SPEC"
else
  FF_BASE_URL="$BASE_URL" npx playwright test --config="$CONFIG" --project="$PROJECT" --list "$SPEC"
fi

echo
echo "=== Running public UX gates ==="
if [[ "$PROJECT" == "all" ]]; then
  FF_BASE_URL="$BASE_URL" npx playwright test --config="$CONFIG" --workers=1 "$SPEC"
else
  FF_BASE_URL="$BASE_URL" npx playwright test --config="$CONFIG" --project="$PROJECT" --workers=1 "$SPEC"
fi

cat > "$OUT_DIR/public-ux-gates-summary.txt" <<EOF
Public UX gates passed.

Base URL: $BASE_URL

Templates verified:
- Homepage: $BASE_URL/platform/
- Campaign: $BASE_URL/c/connect-atx-elite

Checks:
- Homepage UX gate
- Campaign UX gate
- Campaign sponsor/FAQ interaction gate
- No bad-copy tokens
- No console-breaking page errors
- No horizontal mobile overflow
- Campaign media images render
EOF

echo
echo "✅ Public smoke passed."
echo "✅ Public UX gates passed."
echo
echo "Summaries:"
echo "- $OUT_DIR/public-smoke-summary.txt"
echo "- $OUT_DIR/public-ux-gates-summary.txt"

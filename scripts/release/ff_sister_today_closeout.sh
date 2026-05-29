#!/usr/bin/env bash
set -uo pipefail

cd /home/elCUCO/futurefunded-final

mkdir -p audit_outputs/launch-closeout/latest docs/launch-closeout

export FF_ASSET_V="${FF_ASSET_V:-sister-closeout-$(date +%Y%m%d%H%M%S)}"

echo
echo "FutureFunded sister-today closeout"
echo "================================="
echo "Asset version: $FF_ASSET_V"
echo

echo "1) Restarting local PM2 app..."
pm2 restart futurefunded-web --update-env
sleep 2

echo
echo "2) Crawling local launch surfaces..."
python scripts/audit/ff_closeout_surface_map.py \
  --base "http://127.0.0.1:5000" \
  --label "local-pm2" \
  --asset-v "$FF_ASSET_V" \
  --include-auth-dashboard \
  --max-depth 1 \
  --max-pages 90 \
  --output-dir "audit_outputs/launch-closeout/latest/local"
LOCAL_STATUS=$?
cp docs/launch-closeout/sister-today-roadmap.md docs/launch-closeout/local-roadmap.md 2>/dev/null || true

echo
echo "3) Crawling live public surfaces..."
python scripts/audit/ff_closeout_surface_map.py \
  --base "https://getfuturefunded.com" \
  --label "live-public" \
  --asset-v "$FF_ASSET_V" \
  --max-depth 1 \
  --max-pages 90 \
  --output-dir "audit_outputs/launch-closeout/latest/live" || true
cp docs/launch-closeout/sister-today-roadmap.md docs/launch-closeout/live-roadmap.md 2>/dev/null || true

echo
echo "4) Running visual surface board..."
if [ -f scripts/audit/ff_visual_surface_board.mjs ]; then
  node scripts/audit/ff_visual_surface_board.mjs
else
  echo "SKIP: scripts/audit/ff_visual_surface_board.mjs not found"
fi

echo
echo "5) Running Stripe network preflight..."
if [ -f scripts/release/verify-stripe-network.sh ]; then
  bash scripts/release/verify-stripe-network.sh || true
else
  echo "SKIP: scripts/release/verify-stripe-network.sh not found"
fi

echo
echo "6) Git status..."
git status --short

echo
echo "Closeout roadmap:"
echo "docs/launch-closeout/sister-today-roadmap.md"
echo
echo "Latest audit JSON:"
echo "audit_outputs/launch-closeout/latest/surface-map.json"
echo
echo "Latest audit MD:"
echo "audit_outputs/launch-closeout/latest/surface-roadmap.md"
echo

if [ "$LOCAL_STATUS" -ne 0 ]; then
  echo "RESULT: Local crawl found P0 blockers. Open the roadmap before handoff."
  exit "$LOCAL_STATUS"
fi

echo "RESULT: No local P0 route/status blockers found by closeout crawler."

#!/usr/bin/env bash
set -euo pipefail

echo "== FutureFunded safe visual guard =="

echo
echo "== Dirty production files =="
git status --short

echo
echo "== Block dangerous campaign/runtime changes =="
FORBIDDEN_CHANGED="$(
  git diff --name-only -- \
    apps/web/app/static/js/ff-campaign.js \
    apps/web/app/templates/_base/campaign_base.html \
    apps/web/app/templates/campaign/index.html || true
)"

if [[ -n "${FORBIDDEN_CHANGED}" ]]; then
  echo "❌ Dangerous files changed during visual pass:"
  echo "${FORBIDDEN_CHANGED}"
  echo
  echo "Do not touch campaign runtime/base/index during homepage polish."
  exit 1
fi

echo "✅ Campaign runtime/base/index untouched."

echo
echo "== Confirm safe campaign runtime marker exists =="
if ! grep -q "ff-campaign-safe-runtime-v1" apps/web/app/static/js/ff-campaign.js; then
  echo "❌ Safe campaign runtime marker missing."
  exit 1
fi
echo "✅ Safe campaign runtime marker present."

echo
echo "== CSS syntax/diff sanity =="
git diff --check

echo
echo "Safe visual guard: PASS"

#!/usr/bin/env bash
set +e

ROOT="${FF_ROOT:-$HOME/futurefunded-main}"
cd "$ROOT" || exit 1

export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/v20.20.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
source .venv/bin/activate 2>/dev/null || true

STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/campaign-final-qa-pack-$STAMP"
LATEST="audit_outputs/campaign-final-qa-pack-latest"
mkdir -p "$OUT"
rm -f "$LATEST"
ln -s "$OUT" "$LATEST" 2>/dev/null || true

{
  echo "# FutureFunded Campaign Final QA Pack"
  echo
  echo "Generated: $(date -Iseconds)"
  echo
  echo "## Git"
  git log -8 --decorate --oneline
  echo
  echo "## Runtime click proof"
  ffclick 'header [data-ff-open-checkout]'
  cat audit_outputs/live-debug/latest/click-trace.md
  echo
  echo "## Campaign payment smoke"
  node scripts/campaign-payment-smoke.mjs
  echo
  echo "## Visual board"
  timeout --kill-after=10s 180s npm run board:campaign
  echo
  echo "## Doctor"
  npm run doctor
} 2>&1 | tee "$OUT/report.md"

echo
echo "QA pack report: $OUT/report.md"

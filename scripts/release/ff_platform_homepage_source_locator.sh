#!/usr/bin/env bash
set -Eeuo pipefail

OUT="audit_outputs/platform-homepage-pass/source-locator-$(date +%Y%m%d%H%M%S).txt"
mkdir -p "$(dirname "$OUT")"

echo "== FutureFunded platform homepage source locator ==" | tee "$OUT"
echo "Repo: $(pwd)" | tee -a "$OUT"
echo | tee -a "$OUT"

echo "== Route definitions mentioning platform ==" | tee -a "$OUT"
grep -RIn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
  "platform" apps app routes blueprints . 2>/dev/null \
  | grep -E "route|Blueprint|render_template|template|/platform|def " \
  | head -120 | tee -a "$OUT" || true

echo | tee -a "$OUT"
echo "== Template files containing homepage hero copy ==" | tee -a "$OUT"
grep -RIn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
  "Launch a premium fundraising page|Launch a fundraiser people trust|One polished fundraising page|Live donations|Sponsor-ready|Operator-ready" \
  apps app templates . 2>/dev/null \
  | head -160 | tee -a "$OUT" || true

echo | tee -a "$OUT"
echo "== Static/CSS files likely owning platform page ==" | tee -a "$OUT"
find . \
  -path "*/.git" -prune -o \
  -path "*/node_modules" -prune -o \
  -path "*/.venv" -prune -o \
  -type f \( -name "*.css" -o -name "*.html" -o -name "*.py" -o -name "*.js" \) \
  -print \
  | grep -Ei "platform|home|ff|base|shell|landing|marketing" \
  | sort \
  | tee -a "$OUT"

echo | tee -a "$OUT"
echo "== Git state ==" | tee -a "$OUT"
git status --short | tee -a "$OUT"

echo | tee -a "$OUT"
echo "✅ Source locator saved: $OUT"

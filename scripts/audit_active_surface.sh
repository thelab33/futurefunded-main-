#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
WEB="$ROOT/apps/web"
TEMPLATES="$WEB/app/templates"
STATIC="$WEB/app/static"
CSS="$STATIC/css/ff.css"
OUT="$ROOT/tmp/active-audit-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$OUT"

cd "$WEB"
source ../../.venv/bin/activate

echo "== BOOT APP ==" | tee "$OUT/00-boot.txt"
fuser -k 5000/tcp 2>/dev/null || true
pkill -f 'gunicorn.*127\.0\.0\.1:5000' 2>/dev/null || true
nohup gunicorn -w 2 -b 127.0.0.1:5000 "app:create_app()" > "$OUT/gunicorn.log" 2>&1 &
sleep 3
tail -n 20 "$OUT/gunicorn.log" | tee -a "$OUT/00-boot.txt"

echo
echo "== FETCH LIVE HTML ==" | tee "$OUT/01-fetch.txt"
curl -s "http://127.0.0.1:5000/c/connect-atx-elite?mode=preview&v=$(date +%s)" > "$OUT/campaign.html"
curl -s "http://127.0.0.1:5000/platform?v=$(date +%s)" > "$OUT/platform.html" || true

echo
echo "== LIVE CSS ASSETS ==" | tee "$OUT/02-live-css.txt"
{
  echo "-- campaign"
  rg -o 'href="[^"]+\.css[^"]*"' "$OUT/campaign.html" | sed 's/^href="//; s/"$//' | sort -u || true
  echo
  echo "-- platform"
  rg -o 'href="[^"]+\.css[^"]*"' "$OUT/platform.html" | sed 's/^href="//; s/"$//' | sort -u || true
} | tee "$OUT/02-live-css.txt"

echo
echo "== LIVE JS ASSETS ==" | tee "$OUT/03-live-js.txt"
{
  echo "-- campaign"
  rg -o 'src="[^"]+\.js[^"]*"' "$OUT/campaign.html" | sed 's/^src="//; s/"$//' | sort -u || true
  echo
  echo "-- platform"
  rg -o 'src="[^"]+\.js[^"]*"' "$OUT/platform.html" | sed 's/^src="//; s/"$//' | sort -u || true
} | tee "$OUT/03-live-js.txt"

echo
echo "== BODY / TEMPLATE MARKERS ==" | tee "$OUT/04-markers.txt"
{
  echo "-- campaign"
  rg -n 'ff-body|data-ff-template|data-ff-page|ff-shell--campaign|ff-platformBody' "$OUT/campaign.html" || true
  echo
  echo "-- platform"
  rg -n 'ff-body|data-ff-template|data-ff-page|ff-shell--campaign|ff-platformBody' "$OUT/platform.html" || true
} | tee "$OUT/04-markers.txt"

echo
echo "== TEMPLATE EXTENDS MAP ==" | tee "$OUT/05-extends.txt"
find "$TEMPLATES" -type f ! -name '*.bak.*' ! -name '*.orig' ! -name '*~' -print0 \
  | xargs -0 rg -n -F '{% extends "' \
  | sed "s|$TEMPLATES/||" \
  | tee "$OUT/05-extends.txt"

echo
echo "== TEMPLATE INCLUDE TREE (campaign + platform) ==" | tee "$OUT/06-include-tree.txt"
python3 - <<'PY' | tee "$OUT/06-include-tree.txt"
from pathlib import Path
import re

ROOT = Path("app/templates")
include_re = re.compile(r'{%\s*include\s+"([^"]+)"')

def walk(rel, seen, out):
    if rel in seen:
        return
    seen.add(rel)
    p = ROOT / rel
    if not p.exists():
        out.append(f"MISSING: {rel}")
        return
    out.append(rel)
    text = p.read_text(encoding="utf-8", errors="ignore")
    for inc in include_re.findall(text):
        walk(inc, seen, out)

for entry in [
    "campaign/index.html",
    "platform/index.html",
    "platform/dashboard.html",
    "platform/onboarding.html",
]:
    seen = set()
    out = []
    walk(entry, seen, out)
    print(f"## {entry}")
    for item in out:
        print(item)
    print()
PY

echo
echo "== STATIC ASSET REFS IN TEMPLATES ==" | tee "$OUT/07-template-static-refs.txt"
rg -n 'css/[A-Za-z0-9._/-]+\.css|js/[A-Za-z0-9._/-]+\.js' "$TEMPLATES" \
  | sed "s|$TEMPLATES/||" \
  | tee "$OUT/07-template-static-refs.txt"

echo
echo "== CSS FILES ON DISK ==" | tee "$OUT/08-css-on-disk.txt"
find "$STATIC/css" -maxdepth 1 -type f -name '*.css' | sed "s|$ROOT/||" | sort | tee "$OUT/08-css-on-disk.txt"

echo
echo "== JS FILES ON DISK ==" | tee "$OUT/09-js-on-disk.txt"
find "$STATIC/js" -maxdepth 1 -type f -name '*.js' | sed "s|$ROOT/||" | sort | tee "$OUT/09-js-on-disk.txt"

echo
echo "== DUPLICATE HOTSPOT SELECTORS IN ff.css ==" | tee "$OUT/10-ff-hotspots.txt"
rg -n \
  '10B\. CAMPAIGN FINAL POLISH|\.ff-campaignBody \.sponsorTierCard--featured|\.ff-campaignBody \.ff-sponsorTierCard--featured|\.ff-campaignBody \.ff-topbar__capsule|\.ff-campaignBody \.ff-proofMini|@media \(max-width: 640px\)' \
  "$CSS" | tee "$OUT/10-ff-hotspots.txt" || true

echo
echo "== SIMPLE DUPLICATE SELECTOR AUDIT ==" | tee "$OUT/11-ff-duplicate-selectors.txt"
awk '
/^[[:space:]]*\.[A-Za-z0-9_-][^{]*\{$/ {
  s=$0
  sub(/[[:space:]]*\{$/,"",s)
  gsub(/^[[:space:]]+/,"",s)
  count[s]++
}
END {
  for (k in count) if (count[k] > 1) print count[k], k
}
' "$CSS" | sort -nr | tee "$OUT/11-ff-duplicate-selectors.txt"

echo
echo "== BACKUP / TEMP NOISE ==" | tee "$OUT/12-noise.txt"
find "$ROOT/apps/web/app" -type f \( -name '*.bak.*' -o -name '*.orig' -o -name '*~' \) | sed "s|$ROOT/||" | sort | tee "$OUT/12-noise.txt"

echo
echo "== GIT STATUS ==" | tee "$OUT/13-git-status.txt"
git -C "$ROOT" status --short | tee "$OUT/13-git-status.txt"

echo
echo "AUDIT_DIR=$OUT"

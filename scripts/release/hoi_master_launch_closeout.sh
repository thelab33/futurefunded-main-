#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export PATH="$HOME/.local/bin:$HOME/.volta/bin:$HOME/.nvm/versions/node/v20.20.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
hash -r 2>/dev/null || true

BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/hoi-master-closeout/${STAMP}"
mkdir -p "$OUT"

echo "============================================================"
echo "FutureFunded HOI Master Launch Closeout"
echo "Base URL: $BASE_URL"
echo "Output: $OUT"
echo "============================================================"

echo
echo "== 1. Git state =="
git status --short | tee "$OUT/git-status.txt"
git log --oneline --decorate -n 14 | tee "$OUT/git-log.txt"

echo
echo "== 2. Dangerous runtime guard =="
scripts/audit/ff_safe_visual_guard.sh | tee "$OUT/safe-visual-guard.txt"

echo
echo "== 3. Campaign safe runtime marker =="
grep -n "ff-campaign-safe-runtime-v1" apps/web/app/static/js/ff-campaign.js | tee "$OUT/safe-runtime-marker.txt"

echo
echo "== 4. Campaign architecture contract =="
python - <<'PY' | tee "$OUT/campaign-contract.txt"
from pathlib import Path
import re
import sys

checks = {
  "apps/web/app/templates/campaign/index.html": [
    '{% extends "_base/campaign_base.html" %}',
    "ffCampaignConfig",
    "ffSponsorContract",
    "data-ff-open-checkout",
    "data-ff-donate-trigger",
    "data-ff-payment-trigger",
    "data-ff-share-trigger",
    "data-ff-qr-trigger",
    "data-ff-open-sponsor",
    "data-ff-sponsor-trigger",
  ],
  "apps/web/app/templates/_base/campaign_base.html": [
    "{% extends \"_base/site_base.html\" %}",
    "ffConfig",
    "ffSelectors",
    "ff-campaign.js",
  ],
  "apps/web/app/templates/_partials/ff_shell_header.html": [
    "data-ff-header",
    "ffShellHeader",
    "ff-siteHeader",
  ],
}

failed = False
for file, needles in checks.items():
    text = Path(file).read_text(encoding="utf-8", errors="replace")
    print(f"\n## {file}")
    active_doctype = bool(re.search(r"(?im)^\\s*<!doctype\\b", text))
    print("active doctype:", active_doctype)
    if file != "apps/web/app/templates/_base/site_base.html" and active_doctype:
        failed = True
    for needle in needles:
        ok = needle in text
        print(("✅" if ok else "❌"), needle)
        failed = failed or not ok

sys.exit(1 if failed else 0)
PY

echo
echo "== 5. CSS markers =="
for marker in \
  "ff-platform-safe-polish-v1" \
  "ff-platform-heading-legibility-v2" \
  "ff-campaign-visual-polish-v1" \
  "ff-campaign-shell-layout-authority-v3" \
  "ff-campaign-card-system-v4" \
  "hoi-8a-campaign-flagship-final-v1" \
  "hoi-8b-product-family-final-v1"
do
  echo "-- $marker"
  grep -R "$marker" apps/web/app/static/css || true
done | tee "$OUT/css-markers.txt"

echo
echo "== 6. Restart app =="
export FF_ASSET_V="hoi-master-closeout-${STAMP}"
pm2 restart futurefunded-web --update-env | tee "$OUT/pm2-restart.txt"
sleep 3

echo
echo "== 7. Money proof =="
scripts/demo/ff-money-proof.sh | tee "$OUT/money-proof.txt"

echo
echo "== 8. Visual launch gate =="
FF_BASE_URL="$BASE_URL" \
FF_VISUAL_STRICT=1 \
FF_VISUAL_SURFACE_TIMEOUT_MS=35000 \
timeout --kill-after=20s 360s \
node scripts/release/ff_visual_launch_gate.mjs 2>&1 \
| sed -E 's/(access_token=)[A-Za-z0-9_-]+/\1<redacted>/g' \
| tee "$OUT/visual-launch-gate.txt"

echo
echo "== 9. Build review boards =="
python scripts/audit/ff_make_ui_boards_from_launch_gate.py | tee "$OUT/ui-board.txt"

echo
echo "== 10. HTML route marker smoke =="
python - <<'PY' | tee "$OUT/html-route-smoke.txt"
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os
import time

base = os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000")
routes = [
  "/platform/",
  "/c/connect-atx-elite",
  "/platform/login",
  "/platform/onboarding",
  "/platform/dashboard",
]

markers = ["</html>", "ff.css", "campaign.css", "ff-campaign.js", "data-ff-header"]

for route in routes:
    url = f"{base}{route}?css_v=hoi-closeout-{int(time.time())}"
    print(f"\n== {route} ==")
    try:
        req = Request(url, headers={"Cache-Control": "no-cache"})
        with urlopen(req, timeout=20) as res:
            body = res.read().decode("utf-8", errors="replace")
            print("status:", res.status)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print("status:", e.code)
    except URLError as e:
        print("ERROR:", e)
        continue

    print("bytes:", len(body.encode("utf-8")))
    for marker in markers:
        print(f"{marker}: {body.count(marker)}")
PY

cat > "$OUT/SUMMARY.md" <<SUMMARY
# FutureFunded HOI Master Launch Closeout

Date: ${STAMP}
Base URL: ${BASE_URL}

## Required pass files

- safe-visual-guard.txt
- money-proof.txt
- visual-launch-gate.txt
- html-route-smoke.txt
- ui-board.txt

## Review boards

Run:

\`\`\`bash
python -m http.server 8765 -d audit_outputs/page-ui-board/latest
\`\`\`

Open:

- http://127.0.0.1:8765/desktop.html
- http://127.0.0.1:8765/mobile.html

SUMMARY

ln -sfn "$ROOT/$OUT" audit_outputs/hoi-master-closeout/latest

echo
echo "============================================================"
echo "HOI Master Closeout complete"
echo "Output: $OUT"
echo "Latest: audit_outputs/hoi-master-closeout/latest"
echo "============================================================"

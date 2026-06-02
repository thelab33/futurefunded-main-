#!/usr/bin/env bash
set -Eeuo pipefail

OUT="audit_outputs/campaign-polish/css-locator-$(date +%Y%m%d%H%M%S).txt"
mkdir -p "$(dirname "$OUT")"

echo "== FutureFunded campaign CSS locator ==" | tee "$OUT"
echo "Repo: $(pwd)" | tee -a "$OUT"
echo | tee -a "$OUT"

echo "== Campaign template ownership ==" | tee -a "$OUT"
find apps app -type f \( -name "*.html" -o -name "*.py" \) 2>/dev/null \
  | sort \
  | xargs grep -nE "connect-atx-elite|ff-campaignPage|Fuel the season|Back the season|render_template|campaign" 2>/dev/null \
  | sed -n '1,220p' | tee -a "$OUT" || true

echo | tee -a "$OUT"
echo "== Campaign CSS selectors in static CSS ==" | tee -a "$OUT"
find apps app -type f -name "*.css" 2>/dev/null \
  | sort \
  | xargs grep -nE "\.ff-campaign|ff-campaignPage|campaignHero|campaignDonate|sponsor|progressBar|checkout|donor|media|story|impact|tiers" 2>/dev/null \
  | sed -n '1,260p' | tee -a "$OUT" || true

echo | tee -a "$OUT"
echo "== Campaign template class inventory ==" | tee -a "$OUT"
python - <<'PY' | tee -a "$OUT"
from pathlib import Path
import re

files = []
for root in ["apps", "app"]:
    rp = Path(root)
    if rp.exists():
        files.extend(rp.rglob("*.html"))

for p in sorted(files):
    s = p.read_text(encoding="utf-8", errors="replace")
    if "ff-campaign" not in s and "Fuel the season" not in s and "connect-atx-elite" not in s:
        continue

    classes = sorted(set(
        cls
        for m in re.findall(r'class=["\\']([^"\\']+)["\\']', s)
        for cls in m.split()
        if "ff-" in cls or "campaign" in cls.lower() or "sponsor" in cls.lower()
    ))

    print(f"\n-- {p} --")
    for cls in classes[:260]:
        print(cls)
PY

echo | tee -a "$OUT"
echo "== Git state ==" | tee -a "$OUT"
git status --short | tee -a "$OUT"

echo | tee -a "$OUT"
echo "✅ Saved: $OUT"

#!/usr/bin/env bash
set -Eeuo pipefail

OUT="audit_outputs/onboarding-polish/source-locator-$(date +%Y%m%d%H%M%S).txt"
mkdir -p "$(dirname "$OUT")"

echo "== FutureFunded onboarding source locator ==" | tee "$OUT"
echo "Repo: $(pwd)" | tee -a "$OUT"
echo | tee -a "$OUT"

echo "== Route/template ownership ==" | tee -a "$OUT"
find apps app -type f \( -name "*.py" -o -name "*.html" \) 2>/dev/null \
  | sort \
  | xargs grep -nE "platform/onboarding|onboarding|Prepare the campaign|goes public|render_template" 2>/dev/null \
  | sed -n '1,260p' | tee -a "$OUT" || true

echo | tee -a "$OUT"
echo "== CSS ownership ==" | tee -a "$OUT"
find apps app -type f -name "*.css" 2>/dev/null \
  | sort \
  | xargs grep -nE "onboard|onboarding|ff-onboard|launch|platformOnboarding|campaign.*public|goes public" 2>/dev/null \
  | sed -n '1,320p' | tee -a "$OUT" || true

echo | tee -a "$OUT"
echo "== Onboarding template class inventory ==" | tee -a "$OUT"
python - <<'PY' | tee -a "$OUT"
from pathlib import Path
import re

for root in ["apps", "app"]:
    rp = Path(root)
    if not rp.exists():
        continue
    for p in sorted(rp.rglob("*.html")):
        s = p.read_text(encoding="utf-8", errors="replace")
        low = s.lower()
        if "onboarding" not in low and "prepare the campaign" not in low and "goes public" not in low:
            continue

        classes = sorted(set(
            cls
            for m in re.findall(r'''class=["']([^"']+)["']''', s)
            for cls in m.split()
            if "ff-" in cls or "onboard" in cls.lower() or "platform" in cls.lower()
        ))

        print(f"\n-- {p} --")
        for cls in classes[:320]:
            print(cls)
PY

echo | tee -a "$OUT"
echo "== Current rendered onboarding content sample ==" | tee -a "$OUT"
python - <<'PY' | tee -a "$OUT"
from urllib.request import urlopen
from html.parser import HTMLParser

url = "http://127.0.0.1:5000/platform/onboarding"
html = urlopen(url, timeout=10).read().decode("utf-8", "replace")

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, data):
        t = " ".join(data.split())
        if t:
            self.text.append(t)

parser = TextParser()
parser.feed(html)
print("bytes=", len(html))
print("sample=", " ".join(parser.text[:120])[:2500])
PY

echo | tee -a "$OUT"
echo "== Git state ==" | tee -a "$OUT"
git status --short | tee -a "$OUT"

echo | tee -a "$OUT"
echo "✅ Saved: $OUT"

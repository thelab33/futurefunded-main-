#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${FF_LIVE_BASE_URL:-https://getfuturefunded.com}"
OUT="audit_outputs/live-page-pass/platform-$(date +%Y%m%d%H%M%S)"
mkdir -p "$OUT"

URLS=(
  "$BASE/"
  "$BASE/platform/"
  "$BASE/c/connect-atx-elite"
)

echo "== FutureFunded live page audit =="
echo "OUT=$OUT"

for url in "${URLS[@]}"; do
  safe="$(echo "$url" | sed -E 's#https?://##; s#[^a-zA-Z0-9]+#-#g; s#-$##')"
  echo
  echo "== $url ==" | tee "$OUT/$safe.headers.txt"

  curl -LIs "$url" | tee "$OUT/$safe.headers.txt" | sed -n '1,20p'

  curl -Ls "$url" -o "$OUT/$safe.html"

  python - "$OUT/$safe.html" "$url" <<'PY'
from pathlib import Path
import re, sys, json

path = Path(sys.argv[1])
url = sys.argv[2]
html = path.read_text(encoding="utf-8", errors="replace")

def count(pattern):
    return len(re.findall(pattern, html, flags=re.I | re.S))

title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.I | re.S)
h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, re.I | re.S)
h2s = re.findall(r"<h2\b[^>]*>(.*?)</h2>", html, re.I | re.S)

text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
text = re.sub(r"<[^>]+>", " ", text)
text = re.sub(r"\s+", " ", text).strip()

checks = {
    "url": url,
    "bytes": len(html),
    "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else "",
    "description_present": bool(desc),
    "h1_count": len(h1s),
    "h2_count": len(h2s),
    "cta_count": count(r"Start|Donate|Sponsor|Demo|Launch|Book|Get started|View"),
    "stripe_mentions": count(r"Stripe|payment|checkout|receipt"),
    "sponsor_mentions": count(r"sponsor"),
    "trust_mentions": count(r"secure|trusted|receipt|alert|export|dashboard|ledger|privacy"),
    "og_tags": count(r"<meta[^>]+property=[\"']og:"),
    "twitter_tags": count(r"<meta[^>]+name=[\"']twitter:"),
    "canonical_present": count(r"rel=[\"']canonical[\"']") > 0,
    "images": count(r"<img\b"),
    "buttons_links": count(r"<a\b|<button\b"),
    "forms": count(r"<form\b"),
    "sample_text": text[:700],
}

print(json.dumps(checks, indent=2))
PY

done | tee "$OUT/summary.txt"

echo
echo "✅ Live page audit saved: $OUT"

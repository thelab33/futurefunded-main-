#!/usr/bin/env bash
set -euo pipefail

echo "== FutureFunded campaign template guard =="

echo
echo "== Dirty production files =="
git status --short

echo
echo "== Block runtime/base changes =="
FORBIDDEN_CHANGED="$(
  git diff --name-only -- \
    apps/web/app/static/js/ff-campaign.js \
    apps/web/app/templates/_base/campaign_base.html || true
)"

if [[ -n "${FORBIDDEN_CHANGED}" ]]; then
  echo "❌ Forbidden runtime/base files changed:"
  echo "${FORBIDDEN_CHANGED}"
  exit 1
fi

echo "✅ Campaign runtime/base untouched."

echo
echo "== Confirm safe runtime marker still exists =="
if ! grep -q "ff-campaign-safe-runtime-v1" apps/web/app/static/js/ff-campaign.js; then
  echo "❌ Safe campaign runtime marker missing."
  exit 1
fi
echo "✅ Safe campaign runtime marker present."

echo
echo "== Confirm campaign template architecture =="
python - <<'PY'
from pathlib import Path
import re
import sys

p = Path("apps/web/app/templates/campaign/index.html")
text = p.read_text(encoding="utf-8", errors="replace")

checks = [
    ('{% extends "_base/campaign_base.html" %}', "extends campaign base"),
    ("ffCampaignConfig", "campaign config JSON"),
    ("ffSponsorContract", "sponsor contract JSON"),
    ("data-ff-open-checkout", "checkout open hook"),
    ("data-ff-donate-trigger", "donate trigger hook"),
    ("data-ff-payment-trigger", "payment trigger hook"),
    ("data-ff-share-trigger", "share trigger hook"),
    ("data-ff-qr-trigger", "QR trigger hook"),
    ("data-ff-open-sponsor", "sponsor open hook"),
    ("data-ff-sponsor-trigger", "sponsor trigger hook"),
    ("data-ff-sponsor-package", "sponsor package hook"),
]

failed = False
active_doctype = bool(re.search(r"(?im)^\s*<!doctype\b", text))

print(f"active doctype: {active_doctype}")
if active_doctype:
    print("❌ campaign/index.html should not have an active <!doctype>")
    failed = True

for needle, label in checks:
    ok = needle in text
    print(f"{'✅' if ok else '❌'} {label}")
    failed = failed or not ok

sys.exit(1 if failed else 0)
PY

echo
echo "== Diff syntax sanity =="
git diff --check

echo
echo "Campaign template guard: PASS"

#!/usr/bin/env bash
set -euo pipefail

cd /home/elCUCO/futurefunded-final

echo
echo "FutureFunded Wave 4 Final Funnel Smoke"
echo "======================================"
echo

check_head() {
  local url="$1"
  echo
  echo "HEAD $url"
  curl -sS -I "$url" | sed -n '1,12p'
}

check_get_contains() {
  local url="$1"
  local label="$2"
  local needle="$3"
  local tmp

  tmp="$(mktemp)"

  echo
  echo "GET $url :: $label"

  if ! curl -fsS "$url" -o "$tmp"; then
    echo "❌ fetch failed: $url"
    rm -f "$tmp"
    return 1
  fi

  if grep -qi "$needle" "$tmp"; then
    echo "✅ found: $needle"
    rm -f "$tmp"
    return 0
  fi

  echo "❌ missing: $needle"
  rm -f "$tmp"
  return 1
}

echo "PM2"
pm2 status || true

check_head "http://127.0.0.1:5000/healthz"
check_head "http://127.0.0.1:5000/platform"
check_head "http://127.0.0.1:5000/platform/onboarding"
check_head "http://127.0.0.1:5000/c/connect-atx-elite"
check_head "https://getfuturefunded.com/platform/"
check_head "https://getfuturefunded.com/c/connect-atx-elite"

check_get_contains "http://127.0.0.1:5000/c/connect-atx-elite" "donation contract" "data-ff-open-checkout"
check_get_contains "http://127.0.0.1:5000/c/connect-atx-elite" "sponsor contract" "data-ff-open-sponsor"
check_get_contains "http://127.0.0.1:5000/c/connect-atx-elite" "share contract" "data-ff-share-trigger"
check_get_contains "http://127.0.0.1:5000/c/connect-atx-elite" "checkout shell" "ff-embeddedCheckout"

echo
echo "Lifecycle preview spool"
find instance/email-spool -maxdepth 1 -type f -name '*.json' | sort | tail -8 || true

echo
echo "Final launch audit summary"
python scripts/audit/ff_launch_contract_audit.py \
  --base-url http://127.0.0.1:5000 \
  --live-url https://getfuturefunded.com/platform/ \
  --live-url https://getfuturefunded.com/c/connect-atx-elite >/tmp/ff-wave4-audit.log

LATEST="$(find audit_outputs -maxdepth 1 -type f -name 'ff_launch_contract_audit_*.md' | sort | tail -1)"
sed -n '1,45p' "$LATEST"

echo
echo "✅ Wave 4 smoke complete"

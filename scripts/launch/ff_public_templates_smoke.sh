#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${FF_BASE_URL:-https://getfuturefunded.com}}"
BASE_URL="${BASE_URL%/}"

HOME_URL="$BASE_URL/"
PLATFORM_URL="$BASE_URL/platform/"
CAMPAIGN_URL="$BASE_URL/c/connect-atx-elite"

OUT_DIR="${FF_LAUNCH_OUT_DIR:-tmp/launch-results}"
mkdir -p "$OUT_DIR"

BAD_COPY_RE='>None<|Choose None|undefined|null|NaN|Lorem|TODO'
HOME_MARKER_RE='getfuturefunded-home-2026|Fundraising pages that make your team look ready|ffHomeConfig|Start with a campaign page that already feels trusted'
CAMPAIGN_MARKER_RE='data-ff-media-bound|program-proof|connect-atx-team|Support the season with care|Fuel the season'

pass() { echo "✅ $*"; }
fail() { echo "❌ $*" >&2; exit 1; }

fetch_page() {
  local label="$1"
  local url="$2"
  local file="$3"

  echo
  echo "=== $label ==="
  echo "$url"

  local code
  code="$(curl -L -sS -o "$file" -w "%{http_code}" "$url")"

  echo "HTTP $code"
  [[ "$code" == "200" ]] || fail "$label returned HTTP $code"

  if grep -En "$BAD_COPY_RE" "$file"; then
    fail "$label contains bad-copy tokens"
  fi

  pass "$label loads and bad-copy scan is clean"
}

check_marker() {
  local label="$1"
  local file="$2"
  local pattern="$3"

  if grep -E "$pattern" "$file" >/dev/null; then
    pass "$label markers found"
  else
    echo "Expected marker pattern:"
    echo "$pattern"
    fail "$label missing required markers"
  fi
}

check_asset() {
  local label="$1"
  local url="$2"

  local code
  code="$(curl -L -sS -o /dev/null -w "%{http_code}" "$url")"
  echo "$label -> HTTP $code"
  [[ "$code" == "200" ]] || fail "$label asset failed"
}

HOME_FILE="$OUT_DIR/homepage.html"
PLATFORM_FILE="$OUT_DIR/platform.html"
CAMPAIGN_FILE="$OUT_DIR/campaign.html"

fetch_page "Homepage root" "$HOME_URL" "$HOME_FILE"
fetch_page "Platform homepage template" "$PLATFORM_URL" "$PLATFORM_FILE"
fetch_page "Campaign template" "$CAMPAIGN_URL" "$CAMPAIGN_FILE"

check_marker "Homepage" "$PLATFORM_FILE" "$HOME_MARKER_RE"
check_marker "Campaign" "$CAMPAIGN_FILE" "$CAMPAIGN_MARKER_RE"

echo
echo "=== Static assets ==="
check_asset "CSS" "$BASE_URL/static/css/ff.css?v=public-smoke"
check_asset "Campaign JS" "$BASE_URL/static/js/ff-campaign.js?v=public-smoke"
check_asset "6th Grade proof image" "$BASE_URL/static/images/program-proof/6th-grade.jpg"
check_asset "7th Grade proof image" "$BASE_URL/static/images/program-proof/7th-grade.jpg"
check_asset "8th Grade proof image" "$BASE_URL/static/images/program-proof/8th-grade.jpg"
check_asset "Connect ATX team image" "$BASE_URL/static/images/connect-atx-team.jpg"

cat > "$OUT_DIR/public-smoke-summary.txt" <<EOF
Public smoke passed.

Base URL: $BASE_URL
Homepage root: $HOME_URL
Platform homepage: $PLATFORM_URL
Campaign demo: $CAMPAIGN_URL

Checks:
- Homepage HTTP 200
- Platform homepage HTTP 200
- Campaign HTTP 200
- Homepage required markers present
- Campaign required markers present
- Bad-copy scan clean
- CSS asset OK
- Campaign JS asset OK
- Team/proof image assets OK
EOF

echo
pass "Public smoke passed for homepage + campaign"
echo "Summary: $OUT_DIR/public-smoke-summary.txt"

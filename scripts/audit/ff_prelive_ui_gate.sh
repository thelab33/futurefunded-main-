#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo
echo "FutureFunded Prelive UI Gate"
echo "============================"

FAIL=0

run_step() {
  local label="$1"
  shift

  echo
  echo "▶ $label"
  echo "------------------------------------------------------------"

  if "$@"; then
    echo "PASS: $label"
  else
    echo "FAIL: $label"
    FAIL=1
  fi
}

echo
echo "Repo: $ROOT"
echo "Node: $(node -v 2>/dev/null || echo 'missing')"
echo "Python: $(python3 --version 2>/dev/null || echo 'missing')"

ACTIVE_CSS=(
  apps/web/app/static/css/ff.css
  apps/web/app/static/css/platform-home.css
  apps/web/app/static/css/campaign.css
  apps/web/app/static/css/dashboard.css
  apps/web/app/static/css/login.css
  apps/web/app/static/css/onboarding.css
)

ACTIVE_JS=(
  apps/web/app/static/js/ff-app.js
  apps/web/app/static/js/ff-campaign.js
  apps/web/app/static/js/ff-checkout-direct.js
  apps/web/app/static/js/ff-donation-payload-firewall.js
  apps/web/app/static/js/ff-embedded-checkout.js
  apps/web/app/static/js/ff-launch-completion.js
  apps/web/app/static/js/ff-login.js
  apps/web/app/static/js/ff-operator-dashboard.js
  apps/web/app/static/js/ff-sponsor-modal-contract.js
)

ACTIVE_TEMPLATES=(
  apps/web/app/templates/_base/campaign_base.html
  apps/web/app/templates/_base/site_base.html
  apps/web/app/templates/_partials/ff_dashboard_launch_assistant.html
  apps/web/app/templates/_partials/ff_onboarding_text_to_donate.html
  apps/web/app/templates/campaign/_modals.html
  apps/web/app/templates/campaign/index.html
  apps/web/app/templates/legal/contact.html
  apps/web/app/templates/platform/_provider_readiness_panel.html
  apps/web/app/templates/platform/_sponsor_package_preview.html
  apps/web/app/templates/platform/_sponsor_queue_preview.html
  apps/web/app/templates/platform/dashboard.html
  apps/web/app/templates/platform/dashboard_locked.html
  apps/web/app/templates/platform/index.html
  apps/web/app/templates/platform/login.html
  apps/web/app/templates/platform/onboarding.html
)

run_step "No generated CSS backups in public static/css" bash -lc '
  ! find apps/web/app/static/css -maxdepth 1 -type f -name "*.bak-*" | grep -q .
'

run_step "No malformed paste tokens in active CSS/JS/templates" bash -lc '
  ! grep -HnE "^\s*:\+|\\\;|^\s*\+\s+" \
    apps/web/app/static/css/ff.css \
    apps/web/app/static/css/platform-home.css \
    apps/web/app/static/css/campaign.css \
    apps/web/app/static/css/dashboard.css \
    apps/web/app/static/css/login.css \
    apps/web/app/static/css/onboarding.css \
    apps/web/app/static/js/ff-app.js \
    apps/web/app/static/js/ff-campaign.js \
    apps/web/app/static/js/ff-checkout-direct.js \
    apps/web/app/static/js/ff-donation-payload-firewall.js \
    apps/web/app/static/js/ff-embedded-checkout.js \
    apps/web/app/static/js/ff-launch-completion.js \
    apps/web/app/static/js/ff-login.js \
    apps/web/app/static/js/ff-operator-dashboard.js \
    apps/web/app/static/js/ff-sponsor-modal-contract.js \
    apps/web/app/templates/_base/campaign_base.html \
    apps/web/app/templates/_base/site_base.html \
    apps/web/app/templates/_partials/ff_dashboard_launch_assistant.html \
    apps/web/app/templates/_partials/ff_onboarding_text_to_donate.html \
    apps/web/app/templates/campaign/_modals.html \
    apps/web/app/templates/campaign/index.html \
    apps/web/app/templates/legal/contact.html \
    apps/web/app/templates/platform/_provider_readiness_panel.html \
    apps/web/app/templates/platform/_sponsor_package_preview.html \
    apps/web/app/templates/platform/_sponsor_queue_preview.html \
    apps/web/app/templates/platform/dashboard.html \
    apps/web/app/templates/platform/dashboard_locked.html \
    apps/web/app/templates/platform/index.html \
    apps/web/app/templates/platform/login.html \
    apps/web/app/templates/platform/onboarding.html
'

run_step "CSS brace sanity" python3 - <<'PY2'
from pathlib import Path
import re
import sys

files = [
    Path("apps/web/app/static/css/ff.css"),
    Path("apps/web/app/static/css/platform-home.css"),
    Path("apps/web/app/static/css/campaign.css"),
    Path("apps/web/app/static/css/dashboard.css"),
    Path("apps/web/app/static/css/login.css"),
    Path("apps/web/app/static/css/onboarding.css"),
]

failed = False

for p in files:
    if not p.exists():
        print(f"FAIL missing {p}")
        failed = True
        continue

    s = p.read_text(encoding="utf-8", errors="replace")
    clean = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    delta = clean.count("{") - clean.count("}")

    if delta:
        print(f"FAIL {p}: brace delta {delta}")
        failed = True
    else:
        print(f"PASS {p}")

sys.exit(1 if failed else 0)
PY2

run_step "Active JS syntax check" bash -lc '
  set -e
  for f in \
    apps/web/app/static/js/ff-app.js \
    apps/web/app/static/js/ff-campaign.js \
    apps/web/app/static/js/ff-checkout-direct.js \
    apps/web/app/static/js/ff-donation-payload-firewall.js \
    apps/web/app/static/js/ff-embedded-checkout.js \
    apps/web/app/static/js/ff-launch-completion.js \
    apps/web/app/static/js/ff-login.js \
    apps/web/app/static/js/ff-operator-dashboard.js \
    apps/web/app/static/js/ff-sponsor-modal-contract.js \
    scripts/audit/ff_visual_surface_board.mjs \
    scripts/audit/ff_header_clip_audit.mjs
  do
    [ -f "$f" ] && node --check "$f"
  done
'

run_step "Python syntax check for repo scripts" bash -lc '
  set -e
  files=()
  [ -d scripts/repo ] && while IFS= read -r f; do files+=("$f"); done < <(find scripts/repo -maxdepth 1 -type f -name "*.py" | sort)
  [ -d scripts/launch_gate ] && while IFS= read -r f; do files+=("$f"); done < <(find scripts/launch_gate -maxdepth 1 -type f -name "*.py" | sort)
  if [ "${#files[@]}" -gt 0 ]; then
    python3 -m py_compile "${files[@]}"
  else
    echo "No Python repo/launch scripts found"
  fi
'

run_step "CSS authority marker sanity" bash -lc '
  grep -q "FF_STRIPE_MERCURY_REFINEMENT_V3_START" apps/web/app/static/css/ff.css &&
  grep -q "FF_DASHBOARD_HEADER_CANONICAL_V2_START\|FF_DASHBOARD_HEADER_CANONICAL_V1_START" apps/web/app/static/css/dashboard.css &&
  grep -q "FF_PLATFORM_HOME_HEADER_CANONICAL_V1_START" apps/web/app/static/css/platform-home.css &&
  ! grep -q "FF_DASHBOARD_HEADER_UNIFIED_V32_START" apps/web/app/static/css/ff.css &&
  ! grep -q "FF_DASHBOARD_HEADER_REPAIR_V31_START" apps/web/app/static/css/ff.css
'

run_step "Dashboard template loads dashboard.css after ff.css" python3 - <<'PY2'
from pathlib import Path
import sys

p = Path("apps/web/app/templates/platform/dashboard.html")
s = p.read_text(encoding="utf-8", errors="replace")
ff = s.find("css/ff.css")
dash = s.find("css/dashboard.css")

if ff == -1 or dash == -1 or ff > dash:
    print("FAIL: dashboard CSS order")
    sys.exit(1)

print("PASS: dashboard.css loads after ff.css")
PY2

run_step "Homepage template loads platform-home.css after ff.css" python3 - <<'PY2'
from pathlib import Path
import sys

p = Path("apps/web/app/templates/platform/index.html")
s = p.read_text(encoding="utf-8", errors="replace")
ff = s.find("css/ff.css")
home = s.find("css/platform-home.css")

if ff == -1 or home == -1 or ff > home:
    print("FAIL: homepage CSS order")
    sys.exit(1)

print("PASS: platform-home.css loads after ff.css")
PY2

run_step "Campaign template loads campaign.css after ff.css" python3 - <<'PY2'
from pathlib import Path
import sys

p = Path("apps/web/app/templates/campaign/index.html")
s = p.read_text(encoding="utf-8", errors="replace")
ff = s.find("css/ff.css")
campaign = s.find("css/campaign.css")

if ff == -1 or campaign == -1 or ff > campaign:
    print("FAIL: campaign CSS order")
    sys.exit(1)

print("PASS: campaign.css loads after ff.css")
PY2

if [ -n "${FF_OPERATOR_ACCESS_TOKEN:-}" ] || [ -n "${OPERATOR_ACCESS_TOKEN:-}" ] || [ -n "${FF_DASHBOARD_TOKEN:-}" ]; then
  run_step "Header clipping audit with private dashboard" node scripts/audit/ff_header_clip_audit.mjs
else
  echo
  echo "▶ Header clipping audit with private dashboard"
  echo "------------------------------------------------------------"
  echo "SKIP: no operator token env set; visual board still checks locked dashboard."
fi

run_step "Visual surface board" node scripts/audit/ff_visual_surface_board.mjs

echo
echo "============================"
if [ "$FAIL" -eq 0 ]; then
  echo "PRELIVE UI GATE: PASS"
  exit 0
else
  echo "PRELIVE UI GATE: FAIL"
  exit 1
fi

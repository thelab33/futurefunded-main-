#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/../.." || exit 1

export FF_BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"

source scripts/demo/_ff-proof-lib.sh

trap 'cleanup_stale_proof_processes >/dev/null 2>&1 || true' EXIT

echo "Running FutureFunded money-only proof against: $FF_BASE_URL"

wait_for_health

curl -sS \
  -o /tmp/ff-campaign-check.html \
  -w "Campaign HTTP: %{http_code}\n" \
  "$FF_BASE_URL/c/connect-atx-elite"

python - <<'PY'
from pathlib import Path

html = Path("/tmp/ff-campaign-check.html").read_text(encoding="utf-8", errors="replace")
checks = {
    "route clean": "Internal Server Error" not in html and "Traceback" not in html,
    "campaign base marker": "campaign-index-on-campaign-base-v1" in html,
    "ff-campaign.js rendered": "ff-campaign.js" in html,
    "embedded checkout rendered": "ff-embedded-checkout.js" in html,
    "checkout direct rendered": "ff-checkout-direct.js" in html,
    "firewall rendered": "ff-donation-payload-firewall.js" in html,
    "campaign css rendered": "campaign.css" in html,
    "checkout modal present": 'id="checkout"' in html or "data-ff-checkout-modal" in html,
}
for name, ok in checks.items():
    print(f"{'✅' if ok else '❌'} {name}")
if not all(checks.values()):
    raise SystemExit("Rendered campaign HTML is missing a required runtime contract.")
PY

run_step "Campaign payment smoke" "${FF_SMOKE_TIMEOUT:-210}" \
  "node scripts/campaign-payment-smoke-safe.mjs"

echo
echo "Money proof complete."

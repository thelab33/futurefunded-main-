#!/usr/bin/env bash
set -euo pipefail

cd /home/elCUCO/futurefunded-final

echo FutureFunded Pre-Demo Verify
echo ============================
echo

echo Git status
git status --short
echo

echo PM2
pm2 status
echo

echo Health
curl -fsS http://127.0.0.1:5000/healthz | python -m json.tool
echo

echo Launch/funnel proof
scripts/audit/ff_wave4_final_funnel_smoke.sh
python scripts/audit/ff_wave5c_stripe_checkout_smoke.py
timeout 240s node scripts/audit/ff_wave10a_sponsor_sales_scout.mjs
python scripts/audit/ff_wave10b_sponsor_metadata_smoke.py
python scripts/audit/ff_wave10c_dashboard_review_queue_scout.py
timeout 240s node scripts/audit/ff_wave6_founder_demo_scout.mjs
python scripts/audit/ff_launch_contract_audit.py

echo
echo FutureFunded pre-demo verification complete

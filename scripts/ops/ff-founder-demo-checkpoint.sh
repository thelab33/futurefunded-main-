#!/usr/bin/env bash
set -euo pipefail

cd /home/elCUCO/futurefunded-final

echo
echo "FutureFunded Founder Demo Checkpoint"
echo "==================================="
echo

echo "Git status"
git status --short

echo
echo "Do NOT commit these generated paths:"
echo "  audit_outputs/"
echo "  .ff-backups/"
echo "  instance/email-spool/"
echo "  instance/lifecycle-events.json"

echo
echo "Expected product/app changes worth reviewing:"
echo "  apps/web/app/__init__.py"
echo "  apps/web/app/blueprints/campaign/routes.py"
echo "  apps/web/app/services/ff_lifecycle_*.py"
echo "  apps/web/app/services/ff_transactional_email.py"
echo "  apps/web/app/templates/platform/dashboard_locked.html"
echo "  apps/web/app/templates/platform/onboarding.html"
echo "  apps/web/app/templates/campaign_premium.html"
echo "  apps/web/app/static/css/ff.css"
echo "  apps/web/app/static/css/ff.checkout.css"
echo "  apps/web/app/static/css/platform-home.css"
echo "  apps/web/app/static/css/_quarantine/"
echo "  scripts/audit/"
echo "  scripts/ops/"
echo "  scripts/patches/"
echo "  docs/"

echo
echo "Production smoke"
curl -fsS -I http://127.0.0.1:5000/healthz | sed -n '1,6p'
curl -fsS -I https://getfuturefunded.com/platform/ | sed -n '1,8p'
curl -fsS -I https://getfuturefunded.com/c/connect-atx-elite | sed -n '1,8p'

echo
echo "Latest launch audit summary"
LATEST="$(find audit_outputs -maxdepth 1 -type f -name 'ff_launch_contract_audit_*.md' 2>/dev/null | sort | tail -1 || true)"
if [ -n "${LATEST:-}" ]; then
  sed -n '1,35p' "$LATEST"
else
  echo "No audit report found."
fi

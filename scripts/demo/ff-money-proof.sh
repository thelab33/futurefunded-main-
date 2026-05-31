#!/usr/bin/env bash
# FutureFunded canonical money proof.
# Owns only the current checkout runtime contract:
# - ff-campaign-runtime.js opens the checkout modal
# - ff-checkout-direct.js owns Stripe continuation
# - scripts/campaign-payment-smoke.mjs is the canonical proof

set -u

ROOT="${FF_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT" || exit 1

export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/v20.20.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
source .venv/bin/activate 2>/dev/null || true

export FF_BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"

echo "== FutureFunded money proof =="
echo "ROOT=$ROOT"
echo "FF_BASE_URL=$FF_BASE_URL"

python - <<'PY'
import os
import sys
import urllib.request

base = os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
url = base + "/healthz"

try:
    with urllib.request.urlopen(url, timeout=5) as res:
        if not (200 <= res.status < 400):
            raise RuntimeError(f"health status={res.status}")
    print("✅ app health ready")
except Exception as exc:
    print(f"App not ready yet: {exc}")
    sys.exit(7)
PY

HEALTH_CODE="$?"

if [ "$HEALTH_CODE" != "0" ]; then
  echo "== Starting clean demo server =="
  if command -v ffserver >/dev/null 2>&1; then
    ffserver restart
  elif [ -x scripts/demo/ff-demo-start.sh ]; then
    bash scripts/demo/ff-demo-start.sh
  else
    echo "❌ No ffserver or ff-demo-start.sh available."
    exit 1
  fi
fi

echo
echo "== Running canonical campaign payment smoke =="
node scripts/campaign-payment-smoke.mjs

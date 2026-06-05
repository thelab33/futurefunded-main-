#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/futurefunded-main" || exit 1
source .venv/bin/activate 2>/dev/null || true

echo "== Fresh MAIN canonical board proof =="
echo "Root: $(pwd)"

echo
echo "== Ensure Playwright dependency exists =="
if [ ! -d node_modules/playwright ]; then
  if [ -x scripts/ops/ff-install-visual-board-deps.sh ]; then
    bash scripts/ops/ff-install-visual-board-deps.sh
  elif [ -f package-lock.json ]; then
    npm ci
    npx playwright install chromium
  else
    npm install
    npx playwright install chromium
  fi
else
  echo "✅ Playwright dependency present"
fi

echo
echo "== Resolve or create private local dashboard token =="
TOKEN="$(
python - <<'PY'
from pathlib import Path
import re
import secrets

token = ""

for rel in [".env.local", ".env"]:
    path = Path(rel)
    if not path.exists():
        continue

    text = path.read_text()
    match = re.search(r'^FF_OPERATOR_ACCESS_TOKEN=(?:"([^"]+)"|([^\n#]+))', text, re.M)

    if match:
        token = (match.group(1) or match.group(2) or "").strip()
        if token:
            break

if not token:
    token = secrets.token_urlsafe(48)

path = Path(".env.local")
lines = path.read_text().splitlines() if path.exists() else []
out = []
seen = False

for line in lines:
    if line.startswith("FF_OPERATOR_ACCESS_TOKEN="):
        out.append(f"FF_OPERATOR_ACCESS_TOKEN={token}")
        seen = True
    else:
        out.append(line)

if not seen:
    out.append(f"FF_OPERATOR_ACCESS_TOKEN={token}")

path.write_text("\n".join(out).rstrip() + "\n")
print(token)
PY
)"

if [ -z "$TOKEN" ]; then
  echo "❌ token resolution failed"
  exit 1
fi

echo "✅ token loaded privately. length=${#TOKEN}"

export FF_OPERATOR_ACCESS_TOKEN="$TOKEN"
export FF_DEFAULT_CAMPAIGN_NAME="Connect ATX Elite Season Fund"
export DEMO_CAMPAIGN_NAME="Connect ATX Elite Season Fund"

echo
echo "== Stop old app/board ports =="
fuser -k 8788/tcp 2>/dev/null || true
fuser -k 5000/tcp 2>/dev/null || true

mkdir -p audit_outputs/dev-server

echo
echo "== Start main app with exported dashboard token =="
python -m flask --app apps.web.app:create_app run \
  --host 127.0.0.1 \
  --port 5000 \
  --no-debugger \
  --no-reload \
  > audit_outputs/dev-server/latest.log 2>&1 &

APP_PID="$!"

for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:5000/healthz >/dev/null 2>&1; then
    echo "✅ main app healthy. PID=$APP_PID"
    break
  fi

  if [ "$i" = "60" ]; then
    echo "❌ app did not become healthy"
    sed -n '1,220p' audit_outputs/dev-server/latest.log || true
    exit 1
  fi

  sleep 0.4
done

echo
echo "== Canonical route proof =="
FAIL=0

for path in \
  "/healthz" \
  "/platform/" \
  "/c/connect-atx-elite" \
  "/platform/onboarding" \
  "/platform/login"
do
  code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:5000$path" || true)"
  echo "$code $path"

  if [ "$path" = "/platform/" ]; then
    if [ "$code" != "200" ] && [ "$code" != "308" ]; then
      FAIL=1
    fi
  elif [ "$code" != "200" ]; then
    FAIL=1
  fi
done

if [ "$FAIL" -ne 0 ]; then
  echo "❌ route proof failed"
  exit 1
fi

echo
echo "== Dashboard proof: real dashboard, corrected identity =="
curl -s -L "http://127.0.0.1:5000/platform/dashboard?access_token=${TOKEN}" \
  -o /tmp/ff-dashboard-fresh-proof.html

if grep -q 'data-ff-page="platform-login"\|ff-loginAuthority' /tmp/ff-dashboard-fresh-proof.html; then
  echo "❌ dashboard token rendered login page"
  exit 1
fi

if grep -q "Spring Fundraiser" /tmp/ff-dashboard-fresh-proof.html; then
  echo "❌ dashboard still contains Spring Fundraiser"
  grep -n "Spring Fundraiser" /tmp/ff-dashboard-fresh-proof.html | sed -n '1,20p'
  exit 1
fi

if grep -q "Connect ATX Elite Season Fund\|Connect ATX Elite\|Ready-to-send campaign scripts\|Operator command center" /tmp/ff-dashboard-fresh-proof.html; then
  echo "✅ real dashboard rendered with corrected identity"
else
  echo "❌ expected dashboard markers not found"
  sed -n '1,120p' /tmp/ff-dashboard-fresh-proof.html
  exit 1
fi

echo
echo "== Generate fresh canonical launch board =="
python scripts/visual/ff-launch-surface-board.py --capture-only

LATEST="$(cat audit_outputs/launch-surface-board-latest.txt)"
BOARD_DIR="$(dirname "$LATEST")"

echo
echo "== Latest board =="
echo "$LATEST"

echo
echo "== Token leak guard =="
if grep -n "access_token=" "$LATEST"; then
  echo "❌ token reference found in board HTML"
  exit 1
else
  echo "✅ no access_token in board HTML"
fi

echo
echo "== Latest screenshot set =="
find "$BOARD_DIR" -maxdepth 2 -type f | grep -E '(\.png|index\.html)$' | sort

echo
echo "✅ Fresh MAIN canonical board is green."
echo
echo "Open:"
echo "  http://127.0.0.1:8788/?fresh=$(date +%s)"
echo
echo "Serving latest board now. Press Ctrl+C when done."

python -m http.server 8788 \
  --bind 127.0.0.1 \
  --directory "$BOARD_DIR"

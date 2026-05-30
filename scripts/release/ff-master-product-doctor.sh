#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/master-product-doctor-$STAMP"
mkdir -p "$OUT"

echo "== FutureFunded Product Doctor =="
echo "ROOT=$ROOT"
echo "OUT=$OUT"
echo

run_soft() {
  local label="$1"
  shift
  echo
  echo "== $label =="
  if "$@" 2>&1 | tee "$OUT/${label// /-}.log"; then
    echo "✅ $label"
  else
    echo "⚠️ $label failed; continuing"
  fi
}

run_required() {
  local label="$1"
  shift
  echo
  echo "== $label =="
  if "$@" 2>&1 | tee "$OUT/${label// /-}.log"; then
    echo "✅ $label"
  else
    echo "❌ $label"
    exit 1
  fi
}

echo "== Required files =="
for f in \
  run.py \
  package.json \
  requirements.txt \
  apps/web/app/static/css/ff.css \
  apps/web/app/static/css/campaign.css \
  apps/web/app/templates/campaign/index.html \
  scripts/campaign-payment-smoke.mjs
do
  if [ ! -f "$f" ]; then
    echo "❌ Missing required file: $f"
    exit 1
  fi
  echo "✅ $f"
done

run_soft "python compile run.py" python -m py_compile run.py

if command -v npm >/dev/null 2>&1; then
  run_soft "npm lint" npm run lint
fi

if [ -f scripts/demo/ff-demo-start.sh ]; then
  run_required "demo start" bash scripts/demo/ff-demo-start.sh
fi

echo
echo "== Route smoke =="
for path in /healthz /platform/ /platform/onboarding /platform/login /c/connect-atx-elite; do
  code="$(curl -fsS -o /dev/null -w "%{http_code}" "http://127.0.0.1:5000${path}" || true)"
  echo "$code $path" | tee -a "$OUT/route-smoke.txt"
  if [ "$code" != "200" ]; then
    echo "❌ Route failed: $path returned $code"
    exit 1
  fi
done
echo "✅ route smoke"

if [ -f scripts/demo/ff-fast-proof-strict.sh ]; then
  run_required "fast proof strict" bash scripts/demo/ff-fast-proof-strict.sh
elif [ -f scripts/campaign-payment-smoke.mjs ]; then
  run_required "campaign payment smoke" node scripts/campaign-payment-smoke.mjs
fi

echo
echo "✅ FutureFunded Product Doctor passed"
echo "Report: $OUT"

#!/usr/bin/env bash
set -Eeuo pipefail

# FutureFunded strict fast proof wrapper
# Marker: hoi-demo-proof-strict-fast-wrapper-v1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

: "${FF_BASE_URL:=http://127.0.0.1:5000}"
: "${FF_OPERATOR_ACCESS_TOKEN:=${OPERATOR_ACCESS_TOKEN:-dev-operator-20260529123018}}"
: "${OPERATOR_ACCESS_TOKEN:=${FF_OPERATOR_ACCESS_TOKEN}}"

export FF_BASE_URL FF_OPERATOR_ACCESS_TOKEN OPERATOR_ACCESS_TOKEN

bash scripts/demo/ff-fast-proof.sh

REPORT="audit_outputs/visual-launch-gate/latest/report.md"

if [ -f "$REPORT" ]; then
  if grep -nE "FutureFunded visual launch gate: .*FAIL|Expected status 200 but got 403|Dashboard token .*403|❌" "$REPORT" >/tmp/ff-fast-proof-strict-failures.txt 2>/dev/null; then
    echo
    echo "❌ Strict fast proof found launch-gate failures in $REPORT"
    cat /tmp/ff-fast-proof-strict-failures.txt
    exit 1
  fi
fi

echo
echo "✅ Strict fast proof passed with active operator token."

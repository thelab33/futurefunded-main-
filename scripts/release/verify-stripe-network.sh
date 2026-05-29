#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts/conversion-proof

echo "FutureFunded Stripe network preflight"
echo

check_url() {
  local label="$1"
  local url="$2"

  echo "=== $label ==="
  echo "$url"

  set +e
  output="$(curl -I --connect-timeout 8 --max-time 15 -sS "$url" 2>&1)"
  code="$?"
  set -e

  echo "$output" | head -20

  if [[ "$code" -eq 0 ]]; then
    echo "✅ $label reachable"
    return 0
  fi

  echo "❌ $label unreachable"
  return 1
}

ok=1

check_url "Stripe API" "https://api.stripe.com/v1/checkout/sessions" || ok=0
echo
check_url "Stripe Checkout" "https://checkout.stripe.com" || ok=0
echo
check_url "General HTTPS" "https://example.com" || ok=0

cat > artifacts/conversion-proof/stripe-network-preflight.json <<EOF
{
  "ok": $([[ "$ok" -eq 1 ]] && echo true || echo false),
  "checkedAt": "$(date -Is)",
  "note": "Stripe API may return 401/403 and still count as reachable. Network errors such as 'No route to host' are failures."
}
EOF

echo
if [[ "$ok" -eq 1 ]]; then
  echo "✅ Stripe network preflight passed"
else
  echo "❌ Stripe network preflight failed"
  echo "This is a local networking/WSL/VPN/firewall issue, not a FutureFunded app failure."
  exit 78
fi

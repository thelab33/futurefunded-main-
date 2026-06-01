#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="${1:-.env}"

echo "== FutureFunded env sanity check =="
echo "ENV_FILE=$ENV_FILE"
echo

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Missing $ENV_FILE"
  exit 1
fi

fail=0
warn=0

match_file="$(mktemp)"
trap 'rm -f "$match_file"' EXIT

check_fail() {
  local label="$1"
  local pattern="$2"

  if grep -nE "$pattern" "$ENV_FILE" >"$match_file" 2>/dev/null; then
    echo "❌ $label"
    sed -n '1,20p' "$match_file"
    fail=$((fail + 1))
    echo
  fi
}

check_warn() {
  local label="$1"
  local pattern="$2"

  if grep -nE "$pattern" "$ENV_FILE" >"$match_file" 2>/dev/null; then
    echo "⚠️ $label"
    sed -n '1,20p' "$match_file"
    warn=$((warn + 1))
    echo
  fi
}

check_fail "Stray '.env' line found" '^[[:space:]]*\.env[[:space:]]*$'
check_fail "Conflicting production env in local file" '^(FF_ENV|FLASK_ENV)=production'
check_fail "Old repo DB path found" 'futurefunded-final|futurefunded-product-spine|/home/elCUCO/futurefunded/app/data'
check_fail "Quoted env value with spaces around equals" '^[A-Z0-9_]+[[:space:]]+='
check_fail "Live Stripe/restricted key found" '=(sk_live_|rk_live_|pk_live_)'

# Placeholders are safe. Generated local dev SECRET_KEY is expected.
if grep -nE '=(sk_test_|whsec_)' "$ENV_FILE" \
  | grep -v 'REPLACE_ME' >"$match_file" 2>/dev/null; then
  echo "⚠️ Test Stripe/webhook secret-like value found."
  sed -n '1,20p' "$match_file"
  warn=$((warn + 1))
  echo "Rotate before production if this value was pasted anywhere."
  echo
fi

if grep -q '^DATABASE_URL=sqlite:///' "$ENV_FILE"; then
  if ! grep -q '^DATABASE_URL=sqlite:///instance/futurefunded-dev.db' "$ENV_FILE"; then
    echo "❌ DATABASE_URL is sqlite but not the clean current-repo path."
    grep -n '^DATABASE_URL=' "$ENV_FILE"
    fail=$((fail + 1))
    echo
  fi
fi

if grep -nE 'REPLACE_ME|YOUR_|your-controlled-test-inbox@example.com' "$ENV_FILE" >"$match_file" 2>/dev/null; then
  echo "⚠️ Placeholder values still present."
  sed -n '1,30p' "$match_file"
  warn=$((warn + 1))
  echo
fi

if [ "$fail" -eq 0 ]; then
  echo "✅ Env sanity check passed with $warn warning group(s)."
else
  echo "❌ Env sanity check found $fail blocking issue group(s) and $warn warning group(s)."
  exit 2
fi

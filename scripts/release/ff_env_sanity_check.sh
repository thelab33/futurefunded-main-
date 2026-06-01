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

check_grep() {
  local label="$1"
  local pattern="$2"
  if grep -nE "$pattern" "$ENV_FILE" >/tmp/ff_env_match.txt 2>/dev/null; then
    echo "⚠️ $label"
    sed -n '1,20p' /tmp/ff_env_match.txt
    fail=$((fail + 1))
    echo
  fi
}

check_grep "Stray '.env' line found" '^[[:space:]]*\.env[[:space:]]*$'
check_grep "Conflicting production env in local file" '^(FF_ENV|FLASK_ENV)=production'
check_grep "Old repo DB path found" 'futurefunded-final|futurefunded-product-spine|/home/elCUCO/futurefunded/app/data'
check_grep "Quoted env value with spaces around equals" '^[A-Z0-9_]+[[:space:]]+='
check_grep "Potential real secret present" '=(sk_live_|rk_live_|whsec_|[A-Za-z0-9_-]{40,})'

if grep -q '^DATABASE_URL=sqlite:///' "$ENV_FILE"; then
  if ! grep -q '^DATABASE_URL=sqlite:///instance/futurefunded-dev.db' "$ENV_FILE"; then
    echo "⚠️ DATABASE_URL is sqlite but not the clean current-repo path."
    grep -n '^DATABASE_URL=' "$ENV_FILE"
    fail=$((fail + 1))
    echo
  fi
fi

if [ "$fail" -eq 0 ]; then
  echo "✅ Env sanity check passed."
else
  echo "⚠️ Env sanity check found $fail issue group(s). Review before launch."
  exit 2
fi

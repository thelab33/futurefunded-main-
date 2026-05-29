#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.production}"

if [ ! -f "$ENV_FILE" ]; then
  echo "missing required env file: $ENV_FILE"
  exit 1
fi

echo "== production env audit =="
echo "-- file: $ENV_FILE --"

required_vars=(
  FLASK_DEBUG
  FLASK_ENV
  ENV
  APP_ENV
  SECRET_KEY
  WTF_CSRF_SECRET_KEY
  PUBLIC_BASE_URL
  API_BASE_URL
)

for key in "${required_vars[@]}"; do
  if ! rg -q "^${key}=" "$ENV_FILE"; then
    echo "missing required var: $key"
    exit 1
  fi
done

get_val() {
  local key="$1"
  sed -n "s/^${key}=//p" "$ENV_FILE" | tail -n 1
}

FLASK_DEBUG_VAL="$(get_val FLASK_DEBUG)"
FLASK_ENV_VAL="$(get_val FLASK_ENV)"
ENV_VAL="$(get_val ENV)"
APP_ENV_VAL="$(get_val APP_ENV)"
SECRET_KEY_VAL="$(get_val SECRET_KEY)"
WTF_CSRF_SECRET_KEY_VAL="$(get_val WTF_CSRF_SECRET_KEY)"
PUBLIC_BASE_URL_VAL="$(get_val PUBLIC_BASE_URL)"
API_BASE_URL_VAL="$(get_val API_BASE_URL)"

[ "$FLASK_DEBUG_VAL" = "0" ] || { echo "FLASK_DEBUG must be 0"; exit 1; }
[ "$FLASK_ENV_VAL" = "production" ] || { echo "FLASK_ENV must be production"; exit 1; }
[ "$ENV_VAL" = "production" ] || { echo "ENV must be production"; exit 1; }
[ "$APP_ENV_VAL" = "production" ] || { echo "APP_ENV must be production"; exit 1; }

echo "$PUBLIC_BASE_URL_VAL" | rg -q '^https://[^ ]+$' || { echo "PUBLIC_BASE_URL must be https"; exit 1; }
echo "$API_BASE_URL_VAL" | rg -q '^https://[^ ]+$' || { echo "API_BASE_URL must be https"; exit 1; }

PLACEHOLDER_RE='localhost|127\.0\.0\.1|your-domain\.com|your-real-domain\.com|example\.com|example\.org|example\.net|\.example($|/|:)|\.test($|/|:)|\.invalid($|/|:)|\.local($|/|:)'

echo "$PUBLIC_BASE_URL_VAL" | rg -q "$PLACEHOLDER_RE" && { echo "PUBLIC_BASE_URL still looks placeholder/local"; exit 1; } || true
echo "$API_BASE_URL_VAL" | rg -q "$PLACEHOLDER_RE" && { echo "API_BASE_URL still looks placeholder/local"; exit 1; } || true

echo "$SECRET_KEY_VAL" | rg -q 'change-me|example|placeholder' && { echo "SECRET_KEY still looks placeholder"; exit 1; } || true
echo "$WTF_CSRF_SECRET_KEY_VAL" | rg -q 'change-me|example|placeholder' && { echo "WTF_CSRF_SECRET_KEY still looks placeholder"; exit 1; } || true

[ "${#SECRET_KEY_VAL}" -ge 32 ] || { echo "SECRET_KEY looks too short"; exit 1; }
[ "${#WTF_CSRF_SECRET_KEY_VAL}" -ge 32 ] || { echo "WTF_CSRF_SECRET_KEY looks too short"; exit 1; }

echo
echo "production env audit passed"

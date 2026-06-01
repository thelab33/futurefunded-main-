#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${FF_ROOT:-$HOME/futurefunded-main}"
ENV_FILE="${FF_EMAIL_ENV_FILE:-.env.email.local}"
STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/email-real-send-test-$STAMP"

cd "$ROOT" || exit 1

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Missing $ENV_FILE"
  echo "Create it first and fill in controlled SMTP/provider credentials."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo "== FutureFunded controlled real email send =="
echo "OUT=$OUT"
echo "TEST_TO=${FF_EMAIL_TEST_TO:-}"
echo "OPERATOR_TO=${FF_OPERATOR_NOTIFY_EMAIL:-}"
echo

if [ "${FF_EMAIL_REAL_SEND_CONFIRM:-}" != "SEND_TEST_EMAIL" ]; then
  echo "❌ Safety switch is not enabled."
  echo "Set FF_EMAIL_REAL_SEND_CONFIRM=SEND_TEST_EMAIL inside $ENV_FILE only when ready."
  exit 1
fi

if [ -z "${FF_EMAIL_TEST_TO:-}" ] || [ -z "${FF_OPERATOR_NOTIFY_EMAIL:-}" ]; then
  echo "❌ Controlled recipients are missing."
  exit 1
fi

if [ -z "${FF_SMTP_HOST:-}" ] || [ -z "${FF_EMAIL_FROM:-}" ]; then
  echo "❌ SMTP host or sender is missing."
  exit 1
fi

mkdir -p "$OUT"

.venv/bin/python scripts/release/ff_email_delivery_readiness_gate.py \
  --out "$OUT" \
  --stamp "$STAMP"

echo
echo "✅ Controlled real email delivery test finished."
echo "Evidence: $OUT"
cat "$OUT/email-delivery-readiness-result.json"

#!/usr/bin/env bash
set -euo pipefail

cd /home/elCUCO/futurefunded-final

echo
echo "FutureFunded email lifecycle doctor"
echo "==================================="
echo

python scripts/audit/ff_lifecycle_message_drill.py --json | python -m json.tool

echo
echo "Preview spool files"
find instance/email-spool -maxdepth 1 -type f -name '*.json' 2>/dev/null | sort | tail -10 || true

echo
echo "Provider env check"
python - <<'PY'
import os

keys = [
    "FF_EMAIL_DRY_RUN",
    "FF_EMAIL_FROM",
    "FF_EMAIL_REPLY_TO",
    "FF_SMTP_HOST",
    "FF_SMTP_PORT",
    "FF_SMTP_USERNAME",
    "FF_SMTP_USE_TLS",
]

for key in keys:
    value = os.getenv(key, "")
    shown = "***" if key in {"FF_SMTP_USERNAME"} and value else value
    print(f"{key}={shown}")
PY

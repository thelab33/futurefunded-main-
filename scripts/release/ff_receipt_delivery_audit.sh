#!/usr/bin/env bash
set -uo pipefail

ROOT="${FF_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 1

BASE_URL="${FF_BASE_URL:-https://getfuturefunded.com}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT/audit_outputs/receipt-delivery"
LOG="$LOG_DIR/${TS}-receipt-delivery.log"
LATEST="$LOG_DIR/latest-receipt-delivery.log"

mkdir -p "$LOG_DIR"
: > "$LOG"

say() {
  printf "\n%s\n" "$*" | tee -a "$LOG"
}

mask() {
  sed -E \
    -e 's/(sk_live_|sk_test_|pk_live_|pk_test_|whsec_|SG\.)[A-Za-z0-9_./+=:-]+/\1…MASKED/g' \
    -e 's/(FF_SMTP_PASSWORD=).+/\1…MASKED/g' \
    -e 's/(FF_SMTP_USERNAME=).+/\1…MASKED/g' \
    -e 's/(FF_SMTP_PASSWORD: ).+/\1…MASKED/g' \
    -e 's/(FF_SMTP_USERNAME: ).+/\1…MASKED/g' \
    -e 's/([A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})/…UUID_TOKEN_MASKED/g'
}

say "FutureFunded receipt delivery audit"
say "Base URL: $BASE_URL"
say "Campaign slug: $CAMPAIGN_SLUG"
say "Log: $LOG"

say "1) Latest ledger donation"
LEDGER_JSON="/tmp/ff-ledger-${TS}.json"
curl -fsS "${BASE_URL}/c/${CAMPAIGN_SLUG}/ledger/summary?receipt_delivery_audit=${TS}" > "$LEDGER_JSON"

jq '.totals, .recentDonations[0]' "$LEDGER_JSON" | tee -a "$LOG"

SESSION_ID="$(jq -r '.recentDonations[0].provider_session_id // empty' "$LEDGER_JSON")"
DONOR_EMAIL="$(jq -r '.recentDonations[0].donor_email // empty' "$LEDGER_JSON")"

if [[ -z "$SESSION_ID" || "$SESSION_ID" == "null" ]]; then
  say "❌ No latest donation session found."
  exit 1
fi

say "Latest session: $SESSION_ID"
say "Donor email: $DONOR_EMAIL"

say "2) Session-status verification"
STATUS_JSON="/tmp/ff-session-status-${TS}.json"
curl -fsS "${BASE_URL}/c/${CAMPAIGN_SLUG}/checkout/session-status?session_id=${SESSION_ID}" > "$STATUS_JSON"
jq . "$STATUS_JSON" | tee -a "$LOG"

PAID="$(jq -r '.paid // false' "$STATUS_JSON")"
VERIFIED="$(jq -r '.verified // false' "$STATUS_JSON")"

if [[ "$PAID" != "true" || "$VERIFIED" != "true" ]]; then
  say "❌ Session is not paid+verified. Email audit stopped."
  exit 1
fi

say "✅ Payment is paid+verified."

say "3) Stripe object receipt URL check, if Stripe CLI is available"
if command -v stripe >/dev/null 2>&1; then
  stripe checkout sessions retrieve "$SESSION_ID" \
    --expand payment_intent.latest_charge 2>/tmp/ff-stripe-receipt-error-${TS}.txt \
    | tee /tmp/ff-stripe-session-${TS}.json \
    | jq '{
        id,
        payment_status,
        customer_email,
        customer_details,
        payment_intent: {
          id: .payment_intent.id,
          receipt_email: .payment_intent.receipt_email,
          latest_charge: .payment_intent.latest_charge
        }
      }' 2>/dev/null | tee -a "$LOG" || true

  if [[ -s /tmp/ff-stripe-receipt-error-${TS}.txt ]]; then
    say "Stripe CLI receipt lookup warning:"
    cat /tmp/ff-stripe-receipt-error-${TS}.txt | mask | tee -a "$LOG"
  fi
else
  say "Stripe CLI not available; skipping Stripe receipt URL lookup."
fi

say "4) App email spool check"
if [[ -d instance/email-spool ]]; then
  say "Recent email spool files:"
  find instance/email-spool -maxdepth 1 -type f | sort | tail -30 | tee -a "$LOG"

  say "Receipt-like spool files containing donor/session:"
  python - "$SESSION_ID" "$DONOR_EMAIL" <<'PY' | tee -a "$LOG"
from __future__ import annotations

import json
import sys
from pathlib import Path

session_id = sys.argv[1]
email = sys.argv[2].lower()
spool = Path("instance/email-spool")

matches = []
for path in sorted(spool.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
    text = path.read_text(encoding="utf-8", errors="replace")
    low = text.lower()
    if session_id.lower() in low or (email and email in low) or "receipt" in low:
        try:
            data = json.loads(text)
        except Exception:
            data = {}
        matches.append({
            "file": str(path),
            "subject": data.get("subject") or data.get("Subject"),
            "to": data.get("to") or data.get("recipients") or data.get("recipient"),
            "kind": data.get("kind") or data.get("template") or data.get("type"),
            "contains_session": session_id.lower() in low,
            "contains_email": bool(email and email in low),
        })

for item in matches[:20]:
    print(json.dumps(item, indent=2))

if not matches:
    print("NO_RECEIPT_SPOOL_MATCHES_FOUND")
PY
else
  say "No instance/email-spool directory found."
fi

say "5) Runtime email environment flags"
{
  echo "--- Current shell ---"
  env | grep -Ei 'FF_EMAIL|MAIL_|SMTP|POSTMARK|SENDGRID|EMAIL_DRY|SUPPRESS|RECIPIENT|RECEIPT' || true

  echo "--- PM2 process env ---"
  pm2 env 0 2>/dev/null | grep -Ei 'FF_EMAIL|MAIL_|SMTP|POSTMARK|SENDGRID|EMAIL_DRY|SUPPRESS|RECIPIENT|RECEIPT' || true
} | mask | tee -a "$LOG"

say "6) Receipt/email code references"
rg -n --hidden --glob '!node_modules' --glob '!.git' \
  'donor_receipt|operator_donation_alert|receipt_email|FF_EMAIL_DRY_RUN|MAIL_SUPPRESS|POSTMARK|email-spool|send.*receipt|receipt.*send' \
  apps scripts 2>/dev/null | mask | head -200 | tee -a "$LOG" || true

ln -sf "$LOG" "$LATEST"

say "Receipt delivery audit complete"
say "Log: $LOG"
say "Latest: $LATEST"

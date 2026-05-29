#!/usr/bin/env bash
set -uo pipefail

ROOT="${FF_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 1

BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
CAMPAIGN_SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"
TS="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$ROOT/audit_outputs/paid-state-manual-drill"
LOG="$OUT_DIR/${TS}-paid-state-manual-drill.log"
LATEST="$OUT_DIR/latest-paid-state-manual-drill.log"

mkdir -p "$OUT_DIR"
: > "$LOG"

say() {
  printf "\n%s\n" "$*" | tee -a "$LOG"
}

say "FutureFunded paid-state manual drill"
say "Base URL: $BASE_URL"
say "Campaign: $CAMPAIGN_SLUG"
say "Log: $LOG"

say "Step 1 — current email spool snapshot"
find instance/email-spool -maxdepth 1 -type f 2>/dev/null | sort | tail -20 | tee -a "$LOG" || true

say "Step 2 — run existing Stripe checkout smoke"
python scripts/audit/ff_wave5c_stripe_checkout_smoke.py 2>&1 | tee -a "$LOG"
SMOKE_RC=${PIPESTATUS[0]}

if [[ "$SMOKE_RC" -ne 0 ]]; then
  say "❌ Existing Wave 5C smoke failed. Stop here."
  exit "$SMOKE_RC"
fi

LATEST_JSON="$(ls -t audit_outputs/ff_wave5c_stripe_checkout_smoke_*.json 2>/dev/null | head -1 || true)"

if [[ -z "$LATEST_JSON" ]]; then
  say "❌ Could not find latest Wave 5C JSON report."
  exit 1
fi

say "Step 3 — inspect latest smoke JSON"
say "Latest JSON: $LATEST_JSON"

python - "$LATEST_JSON" <<'PY' | tee -a "$LOG"
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8", errors="replace"))

hits = []

def walk(obj, keypath="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, f"{keypath}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, f"{keypath}[{i}]")
    elif isinstance(obj, str):
        if "checkout.stripe.com" in obj or obj.startswith("cs_test_") or obj.startswith("cs_live_"):
            hits.append((keypath, obj))

walk(data)

print("Detected checkout/session evidence:")
for key, value in hits:
    safe = re.sub(r"(cs_(test|live)_[A-Za-z0-9]+)", r"\1", value)
    print(f"- {key}: {safe}")

urls = [value for _, value in hits if "checkout.stripe.com" in value]
sessions = [value for _, value in hits if value.startswith(("cs_test_", "cs_live_"))]

print("")
print("CHECKOUT_URL=" + (urls[0] if urls else ""))
print("SESSION_ID=" + (sessions[0] if sessions else ""))
PY

CHECKOUT_URL="$(python - "$LATEST_JSON" <<'PY'
import json, sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
urls = []

def walk(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            walk(v)
    elif isinstance(obj, list):
        for v in obj:
            walk(v)
    elif isinstance(obj, str) and "checkout.stripe.com" in obj:
        urls.append(obj)

walk(data)
print(urls[0] if urls else "")
PY
)"

SESSION_ID="$(python - "$LATEST_JSON" <<'PY'
import json, sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
sessions = []

def walk(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            walk(v)
    elif isinstance(obj, list):
        for v in obj:
            walk(v)
    elif isinstance(obj, str) and obj.startswith(("cs_test_", "cs_live_")):
        sessions.append(obj)

walk(data)
print(sessions[0] if sessions else "")
PY
)"

say "Step 4 — manual payment instruction"

if [[ -n "$CHECKOUT_URL" ]]; then
  say "Open this Checkout URL and complete payment with Stripe test card:"
  say "$CHECKOUT_URL"
else
  say "No hosted checkout URL was found in the smoke report."
  say "Open the public campaign and click Donate instead:"
  say "$BASE_URL/c/$CAMPAIGN_SLUG"
fi

cat <<'TXT' | tee -a "$LOG"

Use Stripe test card:
  Card: 4242 4242 4242 4242
  Exp: any future date
  CVC: any 3 digits
  ZIP: any 5 digits

Keep stripe listen running in another terminal:
  stripe listen --forward-to http://127.0.0.1:5000/c/stripe/webhook

You want to see:
  checkout.session.completed
  <-- [200] POST http://127.0.0.1:5000/c/stripe/webhook

TXT

read -r -p "After completing the test checkout, press Enter to verify local evidence..."

say "Step 5 — verify session status if session ID was detected"

if [[ -n "$SESSION_ID" ]]; then
  curl -fsS "$BASE_URL/c/$CAMPAIGN_SLUG/checkout/session-status?session_id=$SESSION_ID" | tee -a "$LOG" || true
else
  say "No session ID detected from report; skipping direct session-status check."
fi

say "Step 6 — latest ledger summary"
curl -fsS "$BASE_URL/c/$CAMPAIGN_SLUG/ledger/summary?paid_state_drill=$TS" | tee -a "$LOG" || true

say "Step 7 — latest email spool after checkout"
find instance/email-spool -maxdepth 1 -type f 2>/dev/null | sort | tail -30 | tee -a "$LOG" || true

say "Step 8 — paid-state forensic scan"
python scripts/audit/ff_paid_state_forensics.py 2>&1 | tee -a "$LOG" || true

ln -sf "$LOG" "$LATEST"

say "Paid-state manual drill complete"
say "Log: $LOG"
say "Latest: $LATEST"

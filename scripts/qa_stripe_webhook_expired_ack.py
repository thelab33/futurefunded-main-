#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

if not SECRET:
    print("SKIP: STRIPE_WEBHOOK_SECRET is not set.")
    sys.exit(0)

payload = {
    "id": "evt_expired_contract_test",
    "object": "event",
    "type": "checkout.session.expired",
    "livemode": False,
    "data": {
        "object": {
            "id": "cs_expired_contract_test",
            "object": "checkout.session",
            "payment_status": "unpaid",
            "metadata": {
                "campaign_slug": "connect-atx-elite",
                "flow": "donation",
            },
        }
    },
}

body = json.dumps(payload, separators=(",", ":")).encode()
timestamp = str(int(time.time()))
signed_payload = timestamp.encode() + b"." + body
signature = hmac.new(SECRET.encode(), signed_payload, hashlib.sha256).hexdigest()
stripe_sig = f"t={timestamp},v1={signature}"

req = urllib.request.Request(
    f"{BASE_URL}/c/stripe/webhook",
    data=body,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "Stripe-Signature": stripe_sig,
    },
)

try:
    with urllib.request.urlopen(req, timeout=15) as res:
        status = res.status
        text = res.read().decode("utf-8", "replace")
except urllib.error.HTTPError as e:
    status = e.code
    text = e.read().decode("utf-8", "replace")

print(f"status={status}")
print(text[:500])

if 200 <= status < 300:
    print("OK checkout.session.expired ACKed with 2xx")
    sys.exit(0)

print("FAIL checkout.session.expired returned non-2xx")
sys.exit(1)

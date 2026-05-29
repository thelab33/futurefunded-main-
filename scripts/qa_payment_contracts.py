#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

campaign_url = (
    sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000/c/connect-atx-elite?mode=preview"
)

CAMPAIGN_BASE_URL = campaign_url.split("?", 1)[0].rstrip("/")
WEB_BASE_URL = CAMPAIGN_BASE_URL.rsplit("/c/", 1)[0]


def request_json(url: str, *, method: str = "GET", payload: dict | None = None):
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            data = {"raw": raw}
        return exc.code, data


def campaign_json(path: str, *, method: str = "GET", payload: dict | None = None):
    return request_json(CAMPAIGN_BASE_URL + path, method=method, payload=payload)


def ok(name: str, detail: str = ""):
    print(f"OK {name}{' - ' + detail if detail else ''}")


def fail(name: str, detail: str):
    print(f"FAIL {name} - {detail}")
    raise SystemExit(1)


status, data = campaign_json("/payments/config")
if status == 200 and data.get("endpoints", {}).get("stripeCheckout"):
    ok("payments config returns endpoint JSON")
else:
    fail("payments config", f"status={status} data={data}")


status, data = campaign_json(
    "/checkout/session",
    method="POST",
    payload={"email": "test@example.com"},
)
if status == 400:
    ok("checkout rejects missing amount")
else:
    fail("checkout missing amount", f"status={status} data={data}")


status, data = campaign_json(
    "/checkout/session",
    method="POST",
    payload={"amount": 0, "email": "test@example.com"},
)
if status == 400:
    ok("checkout rejects zero amount")
else:
    fail("checkout zero amount", f"status={status} data={data}")


status, data = campaign_json("/ledger/summary")
if status == 200 and "totals" in data:
    ok("ledger summary returns totals")
else:
    fail("ledger summary", f"status={status} data={data}")


status, data = request_json(
    WEB_BASE_URL + "/c/stripe/webhook",
    method="POST",
    payload={
        "id": "evt_unsigned_contract_test",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_unsigned_contract_test",
                "amount_total": 500,
                "currency": "usd",
                "payment_status": "paid",
                "metadata": {
                    "campaign_slug": "connect-atx-elite",
                    "flow": "donation",
                },
            }
        },
    },
)

if status in (400, 503):
    ok("webhook rejects unsigned or unconfigured request", f"status={status}")
else:
    fail("webhook unsigned request", f"expected 400/503, got status={status} data={data}")


print("Payment contract QA passed")

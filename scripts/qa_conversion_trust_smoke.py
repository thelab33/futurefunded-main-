#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

BASE = os.getenv("FF_QA_BASE_URL", "http://127.0.0.1:5000").rstrip("/")


def fetch(path: str) -> str:
    req = urllib.request.Request(BASE + path, headers={"Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"FAIL fetch {path}: HTTP {exc.code}") from exc


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"FAIL fetch json {path}: HTTP {exc.code}") from exc


def ok(name: str, detail: str = ""):
    print(f"OK {name}{' - ' + detail if detail else ''}")


def fail(name: str, detail: str = ""):
    print(f"FAIL {name}{' - ' + detail if detail else ''}")
    raise SystemExit(1)


platform = fetch("/platform/")
campaign = fetch("/c/connect-atx-elite?mode=preview")
ledger = fetch_json("/c/connect-atx-elite/ledger/summary")

required_platform = [
    "Example data · Live campaign totals.",
]

required_campaign = [
    "Highlighted costs are not the full budget.",
    "Sponsor placements are reviewed before publishing.",
    "brand-safe, family-friendly, and premium",
    "Recent campaign activity",
]

for text in required_platform:
    if text in platform:
        ok("homepage trust copy", text)
    else:
        fail("homepage trust copy missing", text)

for text in [
    "Example campaign metrics shown.",
    "Open the live campaign for current ledger totals.",
]:
    if text in platform:
        fail("old homepage disclosure copy returned", text)
    else:
        ok("old homepage disclosure copy absent", text)

for text in required_campaign:
    if text in campaign:
        ok("campaign trust copy", text)
    else:
        fail("campaign trust copy missing", text)

if "Payment hooks are ready" in campaign:
    fail("old payment-hook copy returned")
else:
    ok("old payment-hook copy absent")

if "data-ff-budget-disclosure" in campaign:
    ok("budget disclosure hook present")
else:
    fail("budget disclosure hook missing")

if "data-ff-sponsor-review-note" in campaign:
    ok("sponsor review hook present")
else:
    fail("sponsor review hook missing")

totals = ledger.get("totals") or {}
if "raised_amount_cents" in totals and "donation_count" in totals:
    ok(
        "ledger summary exposes trust metrics",
        f"{totals.get('raised_amount_cents')} cents / {totals.get('donation_count')} gifts",
    )
else:
    fail("ledger summary missing trust metrics")

# Budget ambiguity guard:
# If the page talks about highlighted costs, it must also explicitly state they are not the full budget.
if re.search(r"highlighted costs", campaign, re.I) and "not the full budget" in campaign:
    ok("budget ambiguity guarded")
else:
    fail("budget ambiguity guard missing")

print("Conversion trust smoke passed")

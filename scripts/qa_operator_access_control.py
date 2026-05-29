#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirectHandler)

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")

TOKEN = os.getenv("FF_QA_OPERATOR_TOKEN") or os.getenv("FF_OPERATOR_ACCESS_TOKEN") or ""


def request(path: str, *, method: str = "GET", payload: dict | None = None, token: str = ""):
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["X-FF-Operator-Token"] = token

    req = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)

    try:
        with OPENER.open(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def ok(name: str, detail: str = ""):
    print(f"OK {name}{' - ' + detail if detail else ''}")


def fail(name: str, detail: str):
    print(f"FAIL {name} - {detail}")
    raise SystemExit(1)


if not TOKEN:
    status, _ = request("/platform/dashboard")
    if status in (302, 303, 401, 403):
        ok("anonymous dashboard requires login", f"status={status}")
    else:
        fail("anonymous dashboard requires login", f"expected 302/303/401/403, got {status}")

    status, _ = request("/c/connect-atx-elite/ledger/events")
    if status in (401, 403):
        ok("anonymous ledger events rejected", f"status={status}")
    else:
        fail("anonymous ledger events rejected", f"expected 401/403, got {status}")

    status, _ = request("/c/connect-atx-elite/ledger/export.csv")
    if status in (401, 403):
        ok("anonymous ledger export rejected", f"status={status}")
    else:
        fail("anonymous ledger export rejected", f"expected 401/403, got {status}")

    print("Operator access-control QA passed in account-login mode")
    raise SystemExit(0)


protected_gets = [
    "/platform/dashboard",
    "/c/connect-atx-elite/ledger/events",
    "/c/connect-atx-elite/ledger/export.csv",
]

for path in protected_gets:
    status, _ = request(path)
    if status in (401, 403):
        ok(f"rejects anonymous GET {path}", f"status={status}")
    else:
        fail(f"rejects anonymous GET {path}", f"expected 401/403, got {status}")

    status, _ = request(path, token=TOKEN)
    if status == 200:
        ok(f"accepts token GET {path}")
    else:
        fail(f"accepts token GET {path}", f"expected 200, got {status}")


status, _ = request(
    "/c/connect-atx-elite/ledger/offline-donation",
    method="POST",
    payload={"amount": 1, "donor_name": "Access QA"},
)

if status in (401, 403):
    ok("rejects anonymous offline donation", f"status={status}")
else:
    fail("rejects anonymous offline donation", f"expected 401/403, got {status}")


status, body = request(
    "/c/connect-atx-elite/ledger/offline-donation",
    method="POST",
    payload={"amount": 1, "donor_name": "Access QA"},
    token=TOKEN,
)

if status == 201:
    ok("accepts token offline donation")
else:
    fail("accepts token offline donation", f"expected 201, got {status}: {body[:300]}")

print("Operator access-control QA passed")

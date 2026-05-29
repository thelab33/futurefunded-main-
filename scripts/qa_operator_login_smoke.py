#!/usr/bin/env python3
from __future__ import annotations

import http.cookiejar
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = os.getenv("FF_QA_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
EMAIL = os.getenv("FF_QA_OPERATOR_EMAIL", "")
PASSWORD = os.getenv("FF_QA_OPERATOR_PASSWORD", "")


def ok(name: str, detail: str = ""):
    print(f"OK {name}{' - ' + detail if detail else ''}")


def fail(name: str, detail: str):
    print(f"FAIL {name} - {detail}")
    raise SystemExit(1)


if not EMAIL or not PASSWORD:
    print("SKIP operator login smoke - FF_QA_OPERATOR_EMAIL/PASSWORD not set")
    raise SystemExit(0)


jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

login_body = urllib.parse.urlencode({"email": EMAIL, "password": PASSWORD}).encode("utf-8")
login_req = urllib.request.Request(
    BASE + "/platform/login",
    data=login_body,
    method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)

try:
    resp = opener.open(login_req, timeout=15)
    status = resp.status
except urllib.error.HTTPError as exc:
    status = exc.code

if status not in (200, 302):
    fail("operator login submit", f"unexpected status={status}")

ok("operator login submit", f"status={status}")

dashboard_req = urllib.request.Request(BASE + "/platform/dashboard", method="GET")
try:
    dashboard_resp = opener.open(dashboard_req, timeout=15)
    dashboard_status = dashboard_resp.status
    body = dashboard_resp.read().decode("utf-8")
except urllib.error.HTTPError as exc:
    dashboard_status = exc.code
    body = exc.read().decode("utf-8")

if dashboard_status == 200 and "data-ff-operator-root" in body:
    ok("operator session opens dashboard")
else:
    fail("operator session opens dashboard", f"status={dashboard_status}")

events_req = urllib.request.Request(BASE + "/c/connect-atx-elite/ledger/events", method="GET")
try:
    events_resp = opener.open(events_req, timeout=15)
    events_status = events_resp.status
except urllib.error.HTTPError as exc:
    events_status = exc.code

if events_status == 200:
    ok("operator session can read ledger events")
else:
    fail("operator session can read ledger events", f"status={events_status}")

print("Operator login QA passed")

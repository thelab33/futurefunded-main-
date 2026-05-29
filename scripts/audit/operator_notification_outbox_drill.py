#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener
import http.cookiejar


def request(opener, method, url, *, form=None, json_payload=None):
    body = None
    headers = {
        "User-Agent": "FutureFunded-Operator-Notification-Outbox-Drill/1.0",
        "Accept": "text/html,application/json,*/*",
    }

    if json_payload is not None:
        body = json.dumps(json_payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
    elif form is not None:
        body = urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = Request(url, data=body, headers=headers, method=method)

    try:
        with opener.open(req, timeout=30) as response:
            return response.status, response.read().decode("utf-8", errors="replace"), response.geturl()
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), exc.geturl()
    except URLError as exc:
        return None, str(exc), url


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []

    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except Exception:
            pass
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify operator notification outbox records are created.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--email", default="arodgps@gmail.com")
    parser.add_argument("--password", default="FF-Launch-7qR9m2vK-2026")
    parser.add_argument("--outbox", default="instance/operator-notification-outbox.jsonl")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    outbox = Path(args.outbox)

    print("\n🚀 FutureFunded operator notification outbox drill")
    print(f"Base URL: {base}")
    print(f"Outbox:   {outbox}\n")

    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))

    status, body, url = request(
        opener,
        "POST",
        f"{base}/platform/login",
        form={
            "email": args.email,
            "password": args.password,
            "next": "/platform/dashboard",
        },
    )

    ok = status == 200 and ("/platform/dashboard" in url or "Campaign setup records" in body)
    print(("✅" if ok else "❌"), "Login", "—", f"status={status}; url={url}")
    if not ok:
        return 1

    status, body, url = request(opener, "GET", f"{base}/platform/dashboard?css_v=notification-outbox-drill")
    setup_ids = re.findall(r"setup_id=([a-f0-9]{16,64})", body)
    setup_id = setup_ids[0] if setup_ids else ""

    ok = status == 200 and bool(setup_id)
    print(("✅" if ok else "❌"), "Find setup", "—", setup_id[:10] if setup_id else "missing")
    if not ok:
        return 1

    before = len(load_records(outbox))

    status, body, url = request(
        opener,
        "POST",
        f"{base}/platform/setup/{setup_id}/status",
        json_payload={"status": "launch_ready"},
    )

    try:
        data = json.loads(body or "{}")
    except Exception:
        data = {}

    ok = status == 200 and data.get("ok") is True
    print(("✅" if ok else "❌"), "Update setup status", "—", data.get("message", body[:180]))
    if not ok:
        return 1

    records = load_records(outbox)
    after_setup = len(records)

    newest = records[-1] if records else {}
    matches = [
        record for record in records
        if record.get("event_type") == "setup_status_changed"
        and record.get("to")
        and (record.get("metadata") or {}).get("setup_id") == setup_id
    ]

    ok = after_setup >= before and bool(matches)
    print(
        ("✅" if ok else "❌"),
        "Setup outbox record created",
        "—",
        f"before={before}; after={after_setup}; newest={newest.get('event_type')}",
    )

    if not ok:
        return 1

    status, body, url = request(
        opener,
        "POST",
        f"{base}/c/connect-atx-elite/ledger/offline-donation",
        json_payload={
            "amount": "9.00",
            "donor_name": "Outbox Drill Offline Supporter",
            "donor_email": args.email,
            "message": "Operator notification outbox drill offline support.",
            "note": "Automated outbox drill.",
        },
    )

    try:
        data = json.loads(body or "{}")
    except Exception:
        data = {}

    ok = status in {200, 201} and data.get("ok") is True
    print(
        ("✅" if ok else "❌"),
        "Record offline support",
        "—",
        data.get("provider_session_id", data.get("message", body[:180])),
    )

    if not ok:
        return 1

    records = load_records(outbox)
    after_offline = len(records)
    offline_matches = [
        record for record in records
        if record.get("event_type") == "offline_donation_recorded"
        and record.get("to")
        and (record.get("metadata") or {}).get("donor_email") == args.email
    ]

    newest = records[-1] if records else {}
    ok = after_offline >= after_setup and bool(offline_matches)
    print(
        ("✅" if ok else "❌"),
        "Offline support outbox record created",
        "—",
        f"before={after_setup}; after={after_offline}; newest={newest.get('event_type')}",
    )

    if not ok:
        return 1

    print("\n🎉 Operator notification outbox drill passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

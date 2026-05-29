#!/usr/bin/env python3
"""
FutureFunded • Wave 5C Stripe Checkout Smoke

Safe local smoke:
- Checks local campaign route.
- Checks payment config route.
- Creates a test donation checkout session.
- Creates a test sponsor checkout session.
- Checks session-status for created sessions.
- Does NOT complete payment.
- Does NOT send live email.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


BASE = "http://127.0.0.1:5000"
SLUG = "connect-atx-elite"
OUT_DIR = Path("audit_outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def request_json(method: str, path: str, payload: dict | None = None) -> dict:
    url = BASE + path
    body = None
    headers = {
        "Accept": "application/json,text/html,*/*",
        "User-Agent": "FutureFundedWave5CStripeSmoke/1.0",
    }

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
            ctype = resp.headers.get("content-type", "")
            data = None
            if "json" in ctype.lower():
                try:
                    data = json.loads(raw)
                except Exception:
                    data = None

            return {
                "ok": 200 <= resp.status < 400,
                "status": resp.status,
                "url": url,
                "content_type": ctype,
                "json": data,
                "text_preview": raw[:600],
            }

    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        data = None
        try:
            data = json.loads(raw)
        except Exception:
            pass

        return {
            "ok": False,
            "status": exc.code,
            "url": url,
            "content_type": exc.headers.get("content-type", ""),
            "json": data,
            "text_preview": raw[:1200],
        }

    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "url": url,
            "error": f"{type(exc).__name__}: {exc}",
            "json": None,
            "text_preview": "",
        }


def session_id_from(result: dict) -> str:
    data = result.get("json") or {}
    for key in ("id", "session_id", "checkout_session_id"):
        value = data.get(key)
        if value:
            return str(value)
    return ""


def checkout_url_from(result: dict) -> str:
    data = result.get("json") or {}
    for key in ("url", "checkout_url"):
        value = data.get(key)
        if value:
            return str(value)
    return ""


def compact(result: dict) -> dict:
    data = result.get("json")
    return {
        "ok": result.get("ok"),
        "status": result.get("status"),
        "url": result.get("url"),
        "json_keys": sorted(list(data.keys())) if isinstance(data, dict) else [],
        "session_id": session_id_from(result),
        "checkout_url_present": bool(checkout_url_from(result)),
        "provider": data.get("provider") if isinstance(data, dict) else None,
        "error": result.get("error"),
        "text_preview": result.get("text_preview", "")[:500],
    }


def main() -> int:
    started = datetime.now().isoformat(timespec="seconds")

    campaign = request_json("GET", f"/c/{SLUG}")
    config = request_json("GET", f"/c/{SLUG}/payments/config")

    donation_payload = {
        "amount": 25,
        "amount_cents": 2500,
        "frequency": "once",
        "kind": "donation",
        "flow": "donation",
        "source": "wave5c-donation-smoke",
        "supporter_name": "Wave 5C Donor",
        "supporter_email": "wave5c-donor@example.com",
        "donor_name": "Wave 5C Donor",
        "donor_email": "wave5c-donor@example.com",
    }

    sponsor_payload = {
        "amount": 300,
        "amount_cents": 30000,
        "frequency": "once",
        "kind": "sponsor",
        "flow": "sponsor",
        "source": "wave5c-sponsor-smoke",
        "sponsor_tier": "Community Partner",
        "tier": "Community Partner",
        "business_name": "Wave 5C Test Sponsor",
        "sponsor_name": "Wave 5C Test Sponsor",
        "sponsor_email": "wave5c-sponsor@example.com",
        "contact_name": "Wave 5C Operator",
    }

    donation = request_json("POST", f"/c/{SLUG}/checkout/session", donation_payload)
    sponsor = request_json("POST", f"/c/{SLUG}/checkout/session", sponsor_payload)

    donation_sid = session_id_from(donation)
    sponsor_sid = session_id_from(sponsor)

    status_checks = {}

    if donation_sid:
        qs = urllib.parse.urlencode({"session_id": donation_sid})
        status_checks["donation"] = request_json("GET", f"/c/{SLUG}/checkout/session-status?{qs}")

    if sponsor_sid:
        qs = urllib.parse.urlencode({"session_id": sponsor_sid})
        status_checks["sponsor"] = request_json("GET", f"/c/{SLUG}/checkout/session-status?{qs}")

    checks = {
        "campaign_page_ok": bool(campaign.get("ok") and campaign.get("status") == 200),
        "payment_config_ok": bool(config.get("ok")),
        "donation_session_created": bool(donation.get("ok") and donation_sid and checkout_url_from(donation)),
        "sponsor_session_created": bool(sponsor.get("ok") and sponsor_sid and checkout_url_from(sponsor)),
        "donation_status_checked": bool(status_checks.get("donation")),
        "sponsor_status_checked": bool(status_checks.get("sponsor")),
    }

    passed = all(checks.values())

    report = {
        "generated_at": started,
        "base": BASE,
        "slug": SLUG,
        "passed": passed,
        "checks": checks,
        "campaign": compact(campaign),
        "config": compact(config),
        "donation": compact(donation),
        "sponsor": compact(sponsor),
        "session_status": {k: compact(v) for k, v in status_checks.items()},
        "notes": [
            "This smoke creates Stripe Checkout Sessions but does not complete payment.",
            "Lifecycle emails dispatch only after confirmed paid/completed session.",
            "If session creation fails, verify Stripe test secret env and route payload contract.",
        ],
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT_DIR / f"ff_wave5c_stripe_checkout_smoke_{stamp}.json"
    md_path = OUT_DIR / f"ff_wave5c_stripe_checkout_smoke_{stamp}.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 5C Stripe Checkout Smoke")
    lines.append("")
    lines.append(f"- **Generated:** `{started}`")
    lines.append(f"- **Passed:** `{passed}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Result |")
    lines.append("| --- | --- |")
    for key, value in checks.items():
        lines.append(f"| `{key}` | {'✅' if value else '❌'} |")
    lines.append("")
    lines.append("## Sessions")
    lines.append("")
    lines.append("| Flow | HTTP | Session ID | Checkout URL | Provider |")
    lines.append("| --- | ---: | --- | --- | --- |")
    for flow, result in [("donation", donation), ("sponsor", sponsor)]:
        c = compact(result)
        sid = c["session_id"] or "—"
        lines.append(
            f"| {flow} | {c['status']} | `{sid}` | "
            f"{'✅' if c['checkout_url_present'] else '❌'} | `{c['provider'] or '—'}` |"
        )
    lines.append("")
    lines.append("## Session status")
    lines.append("")
    if status_checks:
        lines.append("| Flow | HTTP | JSON keys |")
        lines.append("| --- | ---: | --- |")
        for flow, result in status_checks.items():
            c = compact(result)
            lines.append(f"| {flow} | {c['status']} | `{', '.join(c['json_keys'])}` |")
    else:
        lines.append("_No session-status checks ran because no session IDs were returned._")
    lines.append("")
    lines.append("## Failure previews")
    lines.append("")
    for label, result in [("payment_config", config), ("donation", donation), ("sponsor", sponsor)]:
        if result.get("ok"):
            continue
        lines.append(f"### {label}")
        lines.append("```text")
        lines.append(result.get("error") or result.get("text_preview") or "No preview")
        lines.append("```")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 5C Stripe checkout smoke report: {md_path}")
    print(f"JSON: {json_path}")
    print(f"Passed: {passed}")

    if not passed:
        print("")
        print("Failed checks:")
        for key, value in checks.items():
            if not value:
                print(f"  ❌ {key}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

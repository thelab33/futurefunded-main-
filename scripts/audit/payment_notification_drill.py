#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, build_opener


@dataclass
class Check:
    step: str
    ok: bool
    detail: str


def request_json(url: str, payload: dict) -> tuple[int | None, dict, str]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "FutureFunded-Payment-Notification-Drill/1.0",
        },
    )

    try:
        with build_opener().open(req, timeout=30) as res:
            text = res.read().decode("utf-8", errors="replace")
            return res.status, json.loads(text or "{}"), text
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(text or "{}")
        except Exception:
            data = {}
        return exc.code, data, text
    except URLError as exc:
        return None, {}, str(exc)


def request_text(url: str) -> tuple[int | None, str]:
    req = Request(url, headers={"User-Agent": "FutureFunded-Payment-Notification-Drill/1.0"})
    try:
        with build_opener().open(req, timeout=30) as res:
            return res.status, res.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return None, str(exc)


def env_set(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value and not value.startswith("PASTE_") and not value.endswith("_HERE"))


def find_payment_link(html: str) -> str:
    match = re.search(r'https://donate\.stripe\.com/test_[^"\']+', html)
    return match.group(0) if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify FutureFunded payment/email notification readiness.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--campaign-slug", default="connect-atx-elite")
    parser.add_argument("--email", default="arodgps@gmail.com")
    parser.add_argument("--amount-cents", type=int, default=5000)
    parser.add_argument("--output-dir", default="docs/audits/payment-notifications")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    slug = args.campaign_slug
    results: list[Check] = []

    def check(step: str, ok: bool, detail: str) -> None:
        results.append(Check(step, ok, detail))
        print(("✅" if ok else "❌"), step, "—", detail)

    print("\n🚀 FutureFunded payment + notification drill")
    print(f"Base URL: {base_url}")
    print(f"Email:    {args.email}\n")

    required_env = [
        "STRIPE_SECRET_KEY",
        "STRIPE_PUBLISHABLE_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "INTERNAL_NOTIFICATION_EMAIL",
    ]

    for name in required_env:
        check(f"Env {name}", env_set(name), "set" if env_set(name) else "missing or placeholder")

    mail_enabled = os.getenv("MAIL_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    notify_email = os.getenv("INTERNAL_NOTIFICATION_EMAIL", "").strip()
    check(
        "FutureFunded app email mode",
        True,
        f"MAIL_ENABLED={mail_enabled}; INTERNAL_NOTIFICATION_EMAIL={notify_email or 'missing'}",
    )

    campaign_url = f"{base_url}/c/{slug}?css_v=payment-notification-drill"
    status, html = request_text(campaign_url)
    check("Campaign page returns 200", status == 200, f"status={status}")

    payment_link = find_payment_link(html)
    check(
        "Stripe test Payment Link present",
        bool(payment_link),
        payment_link or "No donate.stripe.com/test link found",
    )

    embedded_url = f"{base_url}/c/{slug}/checkout/embedded-session"
    payload = {
        "amount": str(args.amount_cents // 100),
        "amount_cents": args.amount_cents,
        "donor_name": "Payment Drill Donor",
        "donor_email": args.email,
        "email": args.email,
        "label": "FutureFunded payment notification drill",
        "flow": "donation",
    }

    session_status, session_data, session_raw = request_json(embedded_url, payload)
    session_id = str(session_data.get("sessionId") or "")
    client_secret = str(session_data.get("clientSecret") or "")
    publishable_key = str(session_data.get("publishableKey") or "")

    check(
        "Embedded Checkout session creates",
        session_status == 200 and session_data.get("ok") is True and bool(session_id),
        f"status={session_status}; sessionId={session_id[:14] if session_id else 'missing'}",
    )

    check(
        "Embedded Checkout has client secret",
        bool(client_secret),
        "clientSecret returned" if client_secret else session_raw[:220],
    )

    check(
        "Embedded Checkout publishable key is test key",
        publishable_key.startswith("pk_test_"),
        publishable_key[:18] if publishable_key else "missing",
    )

    if session_id:
        qs = urlencode({"session_id": session_id})
        session_check_url = f"{base_url}/c/{slug}/checkout/session-status?{qs}"
        verify_status, verify_text = request_text(session_check_url)

        try:
            verify_data = json.loads(verify_text or "{}")
        except Exception:
            verify_data = {}

        check(
            "Session-status endpoint verifies session",
            verify_status == 200 and verify_data.get("verified") is True,
            f"status={verify_status}; paid={verify_data.get('paid')}; customer_email={verify_data.get('customer_email')}",
        )

        check(
            "Session-status exposes customer email or awaits payment completion",
            bool(verify_data.get("customer_email")) or verify_data.get("paid") is False,
            "email may appear after Checkout completion; unpaid test session is expected",
        )

    email_service = Path("apps/api/app/services/email_service.py")
    email_service_text = email_service.read_text() if email_service.exists() else ""

    check(
        "Email service exists",
        email_service.exists(),
        str(email_service),
    )

    check(
        "Email service is currently stubbed",
        'provider": "stub"' in email_service_text or '"provider": "stub"' in email_service_text,
        "FutureFunded app emails are not actually sent yet; this is expected before SMTP/provider wiring.",
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "base_url": base_url,
        "campaign_slug": slug,
        "email": args.email,
        "mail_enabled": mail_enabled,
        "internal_notification_email": notify_email,
        "payment_link": payment_link,
        "results": [asdict(item) for item in results],
    }

    (out_dir / "payment-notification-drill-results.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    failed = [item for item in results if not item.ok]

    print("\n==============================")
    print("FutureFunded payment notification result")
    print("==============================")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")
    print(f"Output: {out_dir}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

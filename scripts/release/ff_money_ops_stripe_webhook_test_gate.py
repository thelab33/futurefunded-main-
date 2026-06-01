#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))



def cents_from_summary(summary: dict[str, Any]) -> int:
    return int(((summary.get("totals") or {}).get("raised_amount_cents") or 0))


def count_from_summary(summary: dict[str, Any]) -> int:
    return int(((summary.get("totals") or {}).get("donation_count") or 0))


def compact_json(data: dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=False)


def stripe_signature(payload: str, secret: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{payload}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def parse_json_response(response) -> dict[str, Any]:
    text = response.get_data(as_text=True)
    try:
        return json.loads(text)
    except Exception:
        return {"_raw": text[:2000]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--slug", default="connect-atx-elite")
    parser.add_argument("--email", default="operator@getfuturefunded.local")
    parser.add_argument("--password", default="FutureFunded!2026")
    parser.add_argument("--stamp", default=str(int(time.time())))
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    webhook_secret = f"whsec_futurefunded_money_ops_1b_{args.stamp}"

    os.environ["STRIPE_WEBHOOK_SECRET"] = webhook_secret
    os.environ["FF_STRIPE_WEBHOOK_SECRET"] = webhook_secret
    os.environ["STRIPE_WEBHOOK_SIGNING_SECRET"] = webhook_secret
    os.environ["FF_PAYMENTS_ENABLED"] = "1"
    os.environ["FF_STRIPE_ENABLED"] = "1"
    os.environ["FF_EXPECT_TEST_PAYMENTS"] = "1"
    os.environ["FF_FORBID_LIVE_KEYS"] = "1"
    os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_futurefunded_money_ops_1b_placeholder")
    os.environ.setdefault("STRIPE_PUBLIC_KEY", "pk_test_futurefunded_money_ops_1b_placeholder")
    os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_futurefunded_money_ops_1b_placeholder")

    from apps.web.app import create_app

    app = create_app()
    app.testing = True
    app.config["STRIPE_WEBHOOK_SECRET"] = webhook_secret
    app.config["FF_STRIPE_WEBHOOK_SECRET"] = webhook_secret
    app.config["STRIPE_WEBHOOK_SIGNING_SECRET"] = webhook_secret
    app.config["FF_PAYMENTS_ENABLED"] = True
    app.config["FF_STRIPE_ENABLED"] = True

    campaign_slug = args.slug
    amount_cents = 2300
    session_id = f"cs_test_money_ops_1b_{args.stamp}"
    payment_intent_id = f"pi_test_money_ops_1b_{args.stamp}"
    event_id = f"evt_test_money_ops_1b_{args.stamp}"
    donor_email = "stripe-supporter@example.com"
    donor_name = "Stripe Money Ops Test Donor"

    with app.test_client() as client:
        before_response = client.get(f"/c/{campaign_slug}/ledger/summary")
        before = parse_json_response(before_response)

        login_response = client.post(
            "/platform/login",
            data={"email": args.email, "password": args.password},
            follow_redirects=False,
        )
        dashboard_response = client.get("/platform/dashboard")
        dashboard_root = "data-ff-dashboard-root" in dashboard_response.get_data(as_text=True)

        event = {
            "id": event_id,
            "object": "event",
            "api_version": "2024-06-20",
            "created": int(time.time()),
            "livemode": False,
            "pending_webhooks": 1,
            "request": {"id": f"req_test_money_ops_1b_{args.stamp}", "idempotency_key": None},
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": session_id,
                    "object": "checkout.session",
                    "mode": "payment",
                    "status": "complete",
                    "payment_status": "paid",
                    "amount_subtotal": amount_cents,
                    "amount_total": amount_cents,
                    "currency": "usd",
                    "client_reference_id": campaign_slug,
                    "payment_intent": payment_intent_id,
                    "customer_email": donor_email,
                    "customer_details": {
                        "email": donor_email,
                        "name": donor_name,
                    },
                    "metadata": {
                        "campaign_slug": campaign_slug,
                        "campaignSlug": campaign_slug,
                        "donor_name": donor_name,
                        "donor_email": donor_email,
                        "message": f"Money Ops Pass 1B signed Stripe webhook proof {args.stamp}",
                        "source": "money_ops_pass_1b",
                    },
                }
            },
        }

        payload = compact_json(event)
        signature = stripe_signature(payload, webhook_secret, int(time.time()))

        webhook_response = client.post(
            "/c/stripe/webhook",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": signature,
                "Accept": "application/json",
            },
        )
        webhook_body = parse_json_response(webhook_response)

        after_response = client.get(f"/c/{campaign_slug}/ledger/summary")
        after = parse_json_response(after_response)

        events_response = client.get(f"/c/{campaign_slug}/ledger/events")
        events_body = parse_json_response(events_response)

        export_response = client.get(f"/c/{campaign_slug}/ledger/export.csv")
        export_text = export_response.get_data(as_text=True)

    before_total = cents_from_summary(before)
    after_total = cents_from_summary(after)
    before_count = count_from_summary(before)
    after_count = count_from_summary(after)

    recent = after.get("recentDonations") or []
    events_text = json.dumps(events_body, sort_keys=True)

    checks = {
        "login_redirect_or_ok": login_response.status_code in {200, 302, 303},
        "dashboard_root_after_login": dashboard_root,
        "webhook_status_ok": 200 <= webhook_response.status_code < 300,
        "webhook_body_ok": bool(webhook_body),
        "ledger_amount_increased": after_total >= before_total + amount_cents,
        "ledger_count_increased": after_count >= before_count + 1,
        "ledger_has_stripe_session": session_id in json.dumps(after, sort_keys=True),
        "ledger_has_stripe_donor": donor_email in json.dumps(after, sort_keys=True) or any(donor_email in str(item) for item in recent),
        "events_endpoint_ok": events_response.status_code == 200,
        "events_mentions_webhook_or_event": (
            event_id in events_text
            or session_id in events_text
            or "checkout.session.completed" in events_text
            or "stripe" in events_text.lower()
        ),
        "export_endpoint_ok": export_response.status_code == 200,
        "csv_has_stripe_session_or_donor": session_id in export_text or donor_email in export_text or payment_intent_id in export_text,
    }

    result = {
        "ok": all(checks.values()),
        "verdict": "PASS_STRIPE_SIGNED_WEBHOOK_LEDGER_WRITE" if all(checks.values()) else "NEEDS_STRIPE_WEBHOOK_WRITE_PATCH",
        "webhook_secret_prefix": webhook_secret[:10] + "<redacted>",
        "campaign_slug": campaign_slug,
        "amount_cents": amount_cents,
        "session_id": session_id,
        "payment_intent_id": payment_intent_id,
        "event_id": event_id,
        "donor_email": donor_email,
        "before": {
            "status": before_response.status_code,
            "donation_count": before_count,
            "raised_amount_cents": before_total,
        },
        "after": {
            "status": after_response.status_code,
            "donation_count": after_count,
            "raised_amount_cents": after_total,
        },
        "login": {
            "status": login_response.status_code,
            "dashboard_root": dashboard_root,
        },
        "webhook": {
            "status": webhook_response.status_code,
            "body": webhook_body,
        },
        "events": {
            "status": events_response.status_code,
            "body": events_body,
        },
        "export": {
            "status": export_response.status_code,
            "preview": export_text[:1200],
        },
        "checks": checks,
    }

    (out / "stripe-webhook-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "stripe-webhook-event.json").write_text(json.dumps(event, indent=2), encoding="utf-8")
    (out / "ledger-before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    (out / "ledger-after.json").write_text(json.dumps(after, indent=2), encoding="utf-8")
    (out / "ledger-events.json").write_text(json.dumps(events_body, indent=2), encoding="utf-8")
    (out / "ledger-export.csv").write_text(export_text, encoding="utf-8")

    print(json.dumps(result, indent=2))

    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
WEB_ROOT = ROOT / "apps/web"
OUT_DIR = ROOT / "audit_outputs/payment-readiness"
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT.resolve()))
sys.path.insert(0, str(WEB_ROOT.resolve()))

CAMPAIGN_SLUG = os.getenv("FF_CAMPAIGN_SLUG", "connect-atx-elite")
EXPECT_TEST_PAYMENTS = os.getenv("FF_EXPECT_TEST_PAYMENTS") == "1"
FORBID_LIVE_KEYS = os.getenv("FF_FORBID_LIVE_KEYS", "1") != "0"

SECRET_PATTERNS = [
    r"sk_live_[A-Za-z0-9_]+",
    r"sk_test_[A-Za-z0-9_]+",
    r"whsec_[A-Za-z0-9_]+",
    r"rk_live_[A-Za-z0-9_]+",
    r"rk_test_[A-Za-z0-9_]+",
]

PUBLIC_KEY_PATTERNS = [
    r"pk_live_[A-Za-z0-9_]+",
    r"pk_test_[A-Za-z0-9_]+",
]


@dataclass
class Gate:
    checks: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def pass_check(self, name: str, details: Any = None) -> None:
        self.checks.append({"name": name, "status": "PASS", "details": details})

    def warn_check(self, name: str, message: str, details: Any = None) -> None:
        self.warnings.append(message)
        self.checks.append({"name": name, "status": "WARN", "message": message, "details": details})

    def fail_check(self, name: str, message: str, details: Any = None) -> None:
        self.errors.append(message)
        self.checks.append({"name": name, "status": "FAIL", "message": message, "details": details})


def redact(text: str) -> str:
    text = re.sub(r"sk_(live|test)_[A-Za-z0-9_]+", r"sk_\1_<redacted>", text)
    text = re.sub(r"pk_(live|test)_[A-Za-z0-9_]+", r"pk_\1_<redacted>", text)
    text = re.sub(r"whsec_[A-Za-z0-9_]+", "whsec_<redacted>", text)
    return text


def load_app(gate: Gate):
    try:
        from app import create_app

        app = create_app()
        gate.pass_check("Flask app import", "create_app loaded")
        return app
    except Exception as exc:
        gate.fail_check("Flask app import", f"create_app failed: {exc}")
        return None


def response_text(response) -> str:
    try:
        return response.get_data(as_text=True)
    except Exception:
        return ""


def check_no_secret_leaks(gate: Gate, label: str, text: str) -> None:
    leaks: list[str] = []
    for pattern in SECRET_PATTERNS:
        leaks.extend(re.findall(pattern, text or ""))

    if leaks:
        gate.fail_check(label, "secret material leaked in response", [redact(x) for x in leaks[:8]])
    else:
        gate.pass_check(label, "no secret key/webhook secret patterns found")



def check_environment_live_key_safety(gate: Gate) -> None:
    if not FORBID_LIVE_KEYS:
        gate.warn_check("live key environment scan", "live key scan disabled with FF_FORBID_LIVE_KEYS=0")
        return

    live_key_vars = []

    for name, value in os.environ.items():
        value = str(value or "")
        if "pk_live_" in value or "sk_live_" in value or "rk_live_" in value:
            live_key_vars.append(name)

    if live_key_vars:
        gate.fail_check(
            "live key environment scan",
            "live Stripe keys are present in this test/demo environment",
            sorted(live_key_vars),
        )
    else:
        gate.pass_check("live key environment scan", "no live Stripe key patterns found in environment")


def check_campaign_html_secrets(gate: Gate, app: Any) -> None:
    route = f"/c/{CAMPAIGN_SLUG}"

    with app.test_client() as client:
        response = client.get(route)
        body = response_text(response)

        if response.status_code != 200:
            gate.fail_check("campaign page response", f"{route} returned {response.status_code}")
            return

        check_no_secret_leaks(gate, "campaign HTML secret leak scan", body)

        hooks = [
            "data-ff-open-checkout",
            "data-ff-donate-trigger",
            "data-ff-payment-trigger",
            "ffCampaignConfig",
        ]
        missing = [token for token in hooks if token not in body]
        if missing:
            gate.fail_check("campaign payment hooks", "missing payment hooks", missing)
        else:
            gate.pass_check("campaign payment hooks", hooks)


def check_payment_config(gate: Gate, app: Any) -> None:
    route = f"/c/{CAMPAIGN_SLUG}/payments/config"

    with app.test_client() as client:
        response = client.get(route)
        body = response_text(response)
        details = {
            "status": response.status_code,
            "content_type": response.content_type,
            "body_preview": redact(body[:800]),
        }

        if response.status_code >= 500:
            gate.fail_check("payments config route", f"{route} returned {response.status_code}", details)
            return

        check_no_secret_leaks(gate, "payments config secret leak scan", body)

        if response.status_code == 200:
            try:
                data = response.get_json(silent=True) or {}
            except Exception:
                data = {}

            serialized = json.dumps(data)
            public_keys = []
            for pattern in PUBLIC_KEY_PATTERNS:
                public_keys.extend(re.findall(pattern, serialized))

            mode = data.get("mode") or data.get("environment") or data.get("stripe_mode") or "unknown"

            stripe_config = data.get("stripe") if isinstance(data.get("stripe"), dict) else {}
            stripe_enabled = bool(stripe_config.get("enabled"))
            publishable_key = str(
                stripe_config.get("publishableKey")
                or stripe_config.get("publishable_key")
                or ""
            ).strip()

            if EXPECT_TEST_PAYMENTS:
                if not stripe_enabled:
                    gate.fail_check(
                        "payments config test mode",
                        "FF_EXPECT_TEST_PAYMENTS=1 requires stripe.enabled=true",
                        details,
                    )
                elif not publishable_key.startswith("pk_test_"):
                    gate.fail_check(
                        "payments config test mode",
                        "FF_EXPECT_TEST_PAYMENTS=1 requires a pk_test_ publishable key",
                        {"mode": mode, "publishable_key_preview": redact(publishable_key[:24])},
                    )
                elif "pk_live_" in serialized:
                    gate.fail_check(
                        "payments config test mode",
                        "live publishable key exposed while test payments are expected",
                        details,
                    )
                else:
                    gate.pass_check(
                        "payments config test mode",
                        {
                            "mode": mode,
                            "stripe_enabled": stripe_enabled,
                            "public_key": redact(publishable_key),
                        },
                    )
            elif public_keys:
                gate.pass_check(
                    "payments config public key",
                    {"mode": mode, "public_key": redact(public_keys[0])},
                )
            else:
                gate.warn_check(
                    "payments config public key",
                    "no Stripe publishable key detected; acceptable only if checkout is disabled or configured elsewhere",
                    details,
                )
        else:
            gate.warn_check("payments config route", f"{route} returned non-200 status {response.status_code}", details)


def post_json(client, route: str, payload: dict[str, Any], headers: dict[str, str] | None = None):
    return client.post(route, data=json.dumps(payload), content_type="application/json", headers=headers or {})


def check_checkout_session(gate: Gate, app: Any) -> None:
    route = f"/c/{CAMPAIGN_SLUG}/checkout/session"

    bad_payloads = [
        {},
        {"amount": -1},
        {"amount": "not-money"},
        {"amount": 0},
        {"amount": 25, "frequency": "once", "source": "payment_readiness_gate"},
    ]

    goodish_payloads = [
        {"amount_cents": 2500, "frequency": "once", "source": "payment_readiness_gate"},
    ]

    with app.test_client() as client:
        for payload in bad_payloads:
            response = post_json(client, route, payload)
            body = response_text(response)
            details = {
                "payload": payload,
                "status": response.status_code,
                "body_preview": redact(body[:500]),
            }

            check_no_secret_leaks(gate, f"checkout bad payload secret scan {payload}", body)

            if response.status_code >= 500:
                gate.fail_check("checkout rejects malformed payloads", "server error for bad payload", details)
            elif response.status_code in {400, 401, 403, 404, 405, 422}:
                gate.pass_check("checkout rejects malformed payloads", details)
            else:
                gate.warn_check(
                    "checkout rejects malformed payloads",
                    f"unexpected status {response.status_code} for malformed payload",
                    details,
                )

        accepted_or_safe = False
        for payload in goodish_payloads:
            response = post_json(client, route, payload)
            body = response_text(response)
            details = {
                "payload": payload,
                "status": response.status_code,
                "content_type": response.content_type,
                "body_preview": redact(body[:700]),
            }

            check_no_secret_leaks(gate, f"checkout valid payload secret scan {payload}", body)

            if response.status_code >= 500:
                gate.fail_check("checkout valid payload", "server error for valid payload shape", details)
            elif response.status_code in {200, 201, 202, 400, 401, 403, 404, 405, 422}:
                accepted_or_safe = True
                gate.pass_check("checkout valid payload safe response", details)
                break

        if not accepted_or_safe:
            gate.warn_check("checkout valid payload", "no safe checkout response observed")


def check_webhook_signature_rejection(gate: Gate, app: Any) -> None:
    candidates = [
        "/c/stripe/webhook",
        "/stripe/webhook",
        "/webhooks/stripe",
    ]

    with app.test_client() as client:
        seen = False

        for route in candidates:
            response = client.post(
                route,
                data=json.dumps({"type": "payment_intent.succeeded", "data": {"object": {}}}),
                content_type="application/json",
            )
            body = response_text(response)
            details = {
                "route": route,
                "status": response.status_code,
                "body_preview": redact(body[:500]),
            }

            if response.status_code == 404:
                continue

            seen = True
            check_no_secret_leaks(gate, f"webhook secret leak scan {route}", body)

            if response.status_code >= 500:
                gate.fail_check("webhook invalid signature rejection", "webhook returned server error", details)
            elif response.status_code in {400, 401, 403}:
                gate.pass_check("webhook invalid signature rejection", details)
            elif response.status_code in {200, 204}:
                gate.fail_check(
                    "webhook invalid signature rejection",
                    "webhook accepted unsigned/invalid payload",
                    details,
                )
            else:
                gate.warn_check(
                    "webhook invalid signature rejection",
                    f"unusual status {response.status_code}",
                    details,
                )

        if not seen:
            gate.warn_check("webhook route discovery", "no Stripe webhook route found among expected candidates")


def check_ledger_routes(gate: Gate, app: Any) -> None:
    routes = [
        f"/c/{CAMPAIGN_SLUG}/ledger/summary",
        f"/c/{CAMPAIGN_SLUG}/ledger/events",
    ]

    with app.test_client() as client:
        for route in routes:
            response = client.get(route)
            body = response_text(response)
            details = {
                "route": route,
                "status": response.status_code,
                "content_type": response.content_type,
                "body_preview": redact(body[:500]),
            }

            check_no_secret_leaks(gate, f"ledger secret leak scan {route}", body)

            if response.status_code >= 500:
                gate.fail_check("ledger route health", f"{route} returned server error", details)
            else:
                gate.pass_check("ledger route health", details)


def check_operator_protection(gate: Gate, app: Any) -> None:
    protected_routes = [
        "/platform/dashboard",
        f"/c/{CAMPAIGN_SLUG}/ledger/export",
        f"/c/{CAMPAIGN_SLUG}/offline-donation",
    ]

    with app.test_client() as client:
        for route in protected_routes:
            response = client.get(route)
            body = response_text(response)
            details = {
                "route": route,
                "status": response.status_code,
                "body_preview": redact(body[:500]),
            }

            check_no_secret_leaks(gate, f"protected route secret leak scan {route}", body)

            if response.status_code in {302, 401, 403, 404, 405}:
                gate.pass_check("operator protected route", details)
            elif response.status_code >= 500:
                gate.fail_check("operator protected route", "server error on protected route", details)
            else:
                gate.warn_check(
                    "operator protected route",
                    f"route may be publicly accessible with status {response.status_code}",
                    details,
                )


def check_env_mode(gate: Gate, app: Any) -> None:
    keys = {
        "ENV": app.config.get("ENV"),
        "DEBUG": app.config.get("DEBUG"),
        "TESTING": app.config.get("TESTING"),
        "PUBLIC_BASE_URL": app.config.get("PUBLIC_BASE_URL"),
        "STRIPE_LIVE_MODE": app.config.get("STRIPE_LIVE_MODE"),
        "FF_PAYMENTS_ENABLED": app.config.get("FF_PAYMENTS_ENABLED"),
        "FF_EMAIL_DRY_RUN": app.config.get("FF_EMAIL_DRY_RUN"),
    }

    gate.pass_check("environment payment mode snapshot", keys)

    if keys.get("DEBUG") is True and os.getenv("FF_EXPECT_PRODUCTION") == "1":
        gate.fail_check("production debug mode", "DEBUG=True while FF_EXPECT_PRODUCTION=1", keys)


def write_report(gate: Gate) -> None:
    report = {
        "ok": not gate.errors,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "campaign_slug": CAMPAIGN_SLUG,
        "errors": gate.errors,
        "warnings": gate.warnings,
        "checks": gate.checks,
    }

    latest_json = OUT_DIR / "latest.json"
    latest_md = OUT_DIR / "latest.md"

    latest_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# FutureFunded Payment Readiness Gate",
        "",
        f"**Status:** {'PASS ✅' if report['ok'] else 'FAIL ❌'}",
        f"**Checked:** {report['checked_at']}",
        "",
        "## Summary",
        "",
        f"- Checks: {len(gate.checks)}",
        f"- Errors: {len(gate.errors)}",
        f"- Warnings: {len(gate.warnings)}",
        f"- Campaign slug: `{CAMPAIGN_SLUG}`",
        "",
        "## Errors",
        "",
        *([f"- {x}" for x in gate.errors] or ["- None"]),
        "",
        "## Warnings",
        "",
        *([f"- {x}" for x in gate.warnings] or ["- None"]),
        "",
        "## Checks",
        "",
    ]

    for check in gate.checks:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(check["status"], "•")
        lines.append(f"- {icon} **{check['name']}**")

    latest_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(latest_md.read_text(encoding="utf-8"))
    print(f"JSON: {latest_json}")
    print(f"Markdown: {latest_md}")


def main() -> int:
    gate = Gate()
    app = load_app(gate)

    if app is not None:
        check_env_mode(gate, app)
        check_environment_live_key_safety(gate)
        check_campaign_html_secrets(gate, app)
        check_payment_config(gate, app)
        check_checkout_session(gate, app)
        check_webhook_signature_rejection(gate, app)
        check_ledger_routes(gate, app)
        check_operator_protection(gate, app)

    write_report(gate)
    return 1 if gate.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

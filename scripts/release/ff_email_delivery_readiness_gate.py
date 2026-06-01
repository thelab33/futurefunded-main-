#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def redacted(value: str) -> str:
    if not value:
        return ""
    return value[:6] + "<redacted>" if len(value) > 6 else "<redacted>"


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on", "send", "enabled"}


def safe_write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def build_message(*, from_email: str, reply_to: str, to_email: str, category: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg["X-FutureFunded-Test"] = "money-ops-pass-2"
    msg["X-FutureFunded-Category"] = category
    msg.set_content(body)
    return msg


def send_smtp(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    use_tls: bool,
    use_ssl: bool,
    message: EmailMessage,
) -> dict[str, Any]:
    started_at = time.time()

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, timeout=25, context=context) as server:
            if username:
                server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=25) as server:
            server.ehlo()
            if use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            if username:
                server.login(username, password)
            server.send_message(message)

    return {
        "sent": True,
        "mode": "smtp",
        "duration_ms": round((time.time() - started_at) * 1000),
        "to": message["To"],
        "subject": message["Subject"],
        "category": message["X-FutureFunded-Category"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--stamp", default=str(int(time.time())))
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    host = env_first("FF_SMTP_HOST", "MAIL_SERVER", "SMTP_HOST")
    port_raw = env_first("FF_SMTP_PORT", "MAIL_PORT", "SMTP_PORT", default="587")
    username = env_first("FF_SMTP_USERNAME", "MAIL_USERNAME", "SMTP_USERNAME")
    password = env_first("FF_SMTP_PASSWORD", "MAIL_PASSWORD", "SMTP_PASSWORD")
    from_email = env_first("FF_EMAIL_FROM", "MAIL_DEFAULT_SENDER", "DEFAULT_FROM_EMAIL")
    reply_to = env_first("FF_EMAIL_REPLY_TO", "REPLY_TO_EMAIL", default=from_email)
    test_to = env_first("FF_EMAIL_TEST_TO", "EMAIL_TEST_TO")
    operator_to = env_first("FF_OPERATOR_NOTIFY_EMAIL", "OPERATOR_NOTIFY_EMAIL", default=test_to)
    use_tls = truthy(env_first("FF_SMTP_USE_TLS", "MAIL_USE_TLS", "SMTP_USE_TLS", default="1"))
    use_ssl = truthy(env_first("FF_SMTP_USE_SSL", "MAIL_USE_SSL", "SMTP_USE_SSL", default="0"))

    try:
        port = int(port_raw)
    except ValueError:
        port = 587

    real_send_confirm = env_first("FF_EMAIL_REAL_SEND_CONFIRM")
    real_send_enabled = real_send_confirm == "SEND_TEST_EMAIL"

    provider = {
        "host_present": bool(host),
        "port": port,
        "username_present": bool(username),
        "password_present": bool(password),
        "from_email_present": bool(from_email),
        "reply_to_present": bool(reply_to),
        "test_to_present": bool(test_to),
        "operator_to_present": bool(operator_to),
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "real_send_confirmed": real_send_enabled,
        "safe_real_send_required_value": "SEND_TEST_EMAIL",
        "redacted": {
            "host": host,
            "username": redacted(username),
            "from_email": from_email,
            "reply_to": reply_to,
            "test_to": test_to,
            "operator_to": operator_to,
        },
    }

    smtp_ready = bool(host and port and from_email and test_to and (password or not username))
    can_attempt_real_send = smtp_ready and real_send_enabled

    planned_messages = [
        {
            "category": "donor_receipt",
            "to": test_to,
            "subject": "FutureFunded test receipt — Connect ATX Elite",
            "body": (
                "This is a controlled FutureFunded Money Ops Pass 2 test receipt.\n\n"
                "No live donor was contacted. This confirms receipt delivery readiness for the configured test inbox.\n"
            ),
        },
        {
            "category": "operator_donation_alert",
            "to": operator_to or test_to,
            "subject": "FutureFunded test operator alert — Connect ATX Elite",
            "body": (
                "This is a controlled FutureFunded Money Ops Pass 2 operator alert.\n\n"
                "No live donor was contacted. This confirms operator notification delivery readiness.\n"
            ),
        },
    ]

    results: list[dict[str, Any]] = []

    if can_attempt_real_send:
        for item in planned_messages:
            message = build_message(
                from_email=from_email,
                reply_to=reply_to,
                to_email=item["to"],
                category=item["category"],
                subject=item["subject"],
                body=item["body"],
            )
            try:
                results.append(
                    send_smtp(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        use_tls=use_tls,
                        use_ssl=use_ssl,
                        message=message,
                    )
                )
            except Exception as exc:
                results.append(
                    {
                        "sent": False,
                        "mode": "smtp_error",
                        "category": item["category"],
                        "to": item["to"],
                        "subject": item["subject"],
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:600],
                    }
                )
    else:
        for item in planned_messages:
            preview_path = out / f"{args.stamp}-{item['category']}-preview.json"
            preview = {
                "sent": False,
                "mode": "preview_only",
                "reason": (
                    "SMTP provider env missing"
                    if not smtp_ready
                    else "Real send not confirmed. Set FF_EMAIL_REAL_SEND_CONFIRM=SEND_TEST_EMAIL to send controlled test emails."
                ),
                "category": item["category"],
                "to": item["to"],
                "subject": item["subject"],
                "body_preview": item["body"],
            }
            safe_write_json(preview_path, preview)
            preview["path"] = str(preview_path)
            results.append(preview)

    checks = {
        "provider_host_present": bool(host),
        "from_email_present": bool(from_email),
        "test_to_present": bool(test_to),
        "operator_to_present": bool(operator_to),
        "real_send_guard_present": real_send_enabled,
        "smtp_ready": smtp_ready,
        "no_uncontrolled_recipient": all(
            item.get("to") in {test_to, operator_to} and item.get("to")
            for item in results
        ),
        "donor_receipt_attempted_or_previewed": any(item.get("category") == "donor_receipt" for item in results),
        "operator_alert_attempted_or_previewed": any(item.get("category") == "operator_donation_alert" for item in results),
        "real_delivery_passed": bool(can_attempt_real_send and all(item.get("sent") for item in results)),
    }

    if checks["real_delivery_passed"]:
        verdict = "PASS_REAL_EMAIL_DELIVERY_TEST"
    elif smtp_ready and not real_send_enabled:
        verdict = "READY_NEEDS_EXPLICIT_SEND_CONFIRM"
    else:
        verdict = "NEEDS_EMAIL_PROVIDER_ENV"

    output = {
        "ok": verdict == "PASS_REAL_EMAIL_DELIVERY_TEST",
        "verdict": verdict,
        "provider": provider,
        "smtp_ready": smtp_ready,
        "real_send_enabled": can_attempt_real_send,
        "results": results,
        "checks": checks,
    }

    safe_write_json(out / "email-delivery-readiness-result.json", output)
    print(json.dumps(output, indent=2))

    return 0 if verdict == "PASS_REAL_EMAIL_DELIVERY_TEST" else 2


if __name__ == "__main__":
    raise SystemExit(main())

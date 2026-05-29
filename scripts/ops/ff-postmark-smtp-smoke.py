#!/usr/bin/env python3
"""
FutureFunded • Postmark SMTP Smoke

Sends one real SMTP test email using FF_SMTP_* env vars.
Does not touch Stripe, ledger, or lifecycle dispatch.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env: {name}")
    return value


def main() -> int:
    dry_run = os.getenv("FF_EMAIL_DRY_RUN", "1").strip() not in {"0", "false", "False", "no", "NO"}

    host = required("FF_SMTP_HOST")
    port = int(os.getenv("FF_SMTP_PORT", "587"))
    username = required("FF_SMTP_USERNAME")
    password = required("FF_SMTP_PASSWORD")

    # FF_SMTP_PLACEHOLDER_GUARD_V1_START
    placeholder_bits = ("PASTE_", "_HERE", "TOKEN_OR", "ACCESS_KEY", "SECRET_KEY")
    if any(bit in username for bit in placeholder_bits) or any(bit in password for bit in placeholder_bits):
        raise SystemExit(
            "SMTP credentials still look like placeholders. "
            "Update ~/.config/futurefunded/postmark.env with real Postmark Server API Token "
            "or SMTP Token credentials before sending."
        )
    # FF_SMTP_PLACEHOLDER_GUARD_V1_END

    sender = required("FF_EMAIL_FROM")
    recipient = required("FF_EMAIL_TEST_TO")
    reply_to = os.getenv("FF_EMAIL_REPLY_TO", "").strip()

    subject = f"FutureFunded SMTP smoke ✅ {datetime.now().isoformat(timespec='seconds')}"
    text = (
        "FutureFunded SMTP smoke passed.\n\n"
        "This confirms the app can authenticate to the transactional email provider.\n"
        "Next step: run lifecycle dispatch with FF_EMAIL_DRY_RUN=0.\n"
    )

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(text)
    msg.add_alternative(
        f"""
        <html>
          <body style="font-family:Arial,sans-serif;line-height:1.5">
            <h2>FutureFunded SMTP smoke passed ✅</h2>
            <p>This confirms FutureFunded can authenticate to the transactional email provider.</p>
            <p><strong>Next step:</strong> run lifecycle dispatch with <code>FF_EMAIL_DRY_RUN=0</code>.</p>
          </body>
        </html>
        """,
        subtype="html",
    )

    print("FutureFunded Postmark SMTP Smoke")
    print("================================")
    print(f"Host: {host}:{port}")
    print(f"From: {sender}")
    print(f"To:   {recipient}")
    print(f"Dry run: {dry_run}")

    if dry_run:
        print("DRY RUN ONLY — set FF_EMAIL_DRY_RUN=0 to send.")
        return 0

    context = ssl.create_default_context()

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        if os.getenv("FF_SMTP_USE_TLS", "1").strip() in {"1", "true", "True", "yes", "YES"}:
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(msg)

    print("✅ SMTP test email sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

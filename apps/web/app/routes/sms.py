from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
from xml.sax.saxutils import escape

from flask import Blueprint, Response, current_app, request

sms_bp = Blueprint("ff_native_sms", __name__)

_TRUE = {"1", "true", "yes", "on", "enabled"}


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _campaign_url() -> str:
    return _env("FF_TEXT_TO_DONATE_URL") or _env("FF_PUBLIC_CAMPAIGN_URL") or "https://getfuturefunded.com/c/connect-atx-elite"


def _keyword() -> str:
    return re.sub(r"[^A-Za-z0-9]", "", _env("FF_TEXT_TO_DONATE_KEYWORD", "ATXELITE")).upper() or "ATXELITE"


def _twiml(message: str, status: int = 200) -> Response:
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(message)}</Message></Response>'
    return Response(xml, status=status, mimetype="application/xml")


def _signature_valid() -> bool:
    validate = _env("FF_TWILIO_VALIDATE_SIGNATURE", "0").lower() in _TRUE
    token = _env("TWILIO_AUTH_TOKEN")

    if not validate:
        return True

    if not token:
        current_app.logger.warning("FF_TWILIO_VALIDATE_SIGNATURE is enabled but TWILIO_AUTH_TOKEN is missing.")
        return False

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    public_base = _env("FF_PUBLIC_BASE_URL")
    if public_base:
        url = public_base.rstrip("/") + request.path
    else:
        url = request.url

    payload = url + "".join(key + value for key, value in sorted(request.form.items()))
    digest = base64.b64encode(hmac.new(token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()).decode("utf-8")

    return hmac.compare_digest(digest, signature)


@sms_bp.route("/sms/twilio/incoming", methods=["GET", "POST"])
def twilio_incoming() -> Response:
    if request.method == "GET":
        return Response(
            {
                "ok": True,
                "provider": "twilio",
                "endpoint": "/sms/twilio/incoming",
                "keyword": _keyword(),
                "campaign_url": _campaign_url(),
            },
            mimetype="application/json",
        )

    if not _signature_valid():
        return _twiml("FutureFunded could not verify this SMS request.", status=403)

    body = (request.form.get("Body") or "").strip()
    normalized = re.sub(r"[^A-Za-z0-9 ]", " ", body).upper()
    keyword = _keyword()
    campaign_url = _campaign_url()

    if "STOP" in normalized:
        return _twiml("You are opted out. No further FutureFunded campaign texts will be sent from this automated line.")

    if "HELP" in normalized:
        return _twiml(f"FutureFunded support: text {keyword} to receive the secure campaign link, or visit {campaign_url}")

    if keyword in normalized or not normalized:
        return _twiml(f"Thanks for supporting Connect ATX Elite. Give securely here: {campaign_url}")

    return _twiml(f"To support Connect ATX Elite, text {keyword} or open the secure campaign link: {campaign_url}")

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "audit"
OUT.mkdir(parents=True, exist_ok=True)

BASE_URL = os.environ.get("FF_AUDIT_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

CSS_RE = re.compile(r'<link[^>]+href=["\']([^"\']+\.css(?:\?[^"\']*)?)["\']', re.I)
JS_RE = re.compile(r'<script[^>]+src=["\']([^"\']+\.js(?:\?[^"\']*)?)["\']', re.I)



def has_sponsor_contract_marker(html: str) -> bool:
    """Return true when the rendered campaign exposes the sponsor contract surface."""
    if not html:
        return False

    markers = (
        "ffSponsorContract",
        "data-ff-sponsor-contract",
        "data-ff-sponsor-contract-script",
        "sponsor-packages-v1",
        "data-ff-sponsor-package",
        "data-ff-sponsor-form",
        "data-ff-sponsor-cta",
        "data-ff-open-sponsor",
        "data-ff-sponsor-trigger",
    )

    return any(marker in html for marker in markers)

def load_env_file(path: Path) -> dict[str, str]:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


_file_env = load_env_file(ROOT / ".env.local")
_shell_env = {k: v for k, v in os.environ.items() if str(v).strip()}
ENV = {**_file_env, **_shell_env}

# Strong local fallback: the Stripe CLI signing secret is often stored here
# even when the current shell does not export it.
_whsec_file = ROOT / ".stripe-local-whsec"
if _whsec_file.exists():
    _whsec = _whsec_file.read_text().strip()
    if _whsec.startswith("whsec_"):
        ENV.setdefault("FF_STRIPE_WEBHOOK_SECRET", _whsec)
        ENV.setdefault("STRIPE_WEBHOOK_SECRET", _whsec)
        ENV.setdefault("STRIPE_WEBHOOK_SIGNING_SECRET", _whsec)


def mask(value: str | None) -> dict:
    value = (value or "").strip()
    return {
        "present": bool(value),
        "prefix": value[:8] + "…" if value else "",
        "length": len(value),
    }


def request(method: str, path: str, body: bytes | None = None, headers: dict | None = None) -> dict:
    url = path if path.startswith("http") else BASE_URL + path
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            raw = res.read()
            text = raw.decode(res.headers.get_content_charset() or "utf-8", errors="replace")
            return {
                "ok": True,
                "status": res.status,
                "url": url,
                "headers": dict(res.headers.items()),
                "text": text,
                "text_len": len(text),
            }
    except urllib.error.HTTPError as e:
        raw = e.read()
        text = raw.decode(e.headers.get_content_charset() or "utf-8", errors="replace")
        return {
            "ok": False,
            "status": e.code,
            "url": url,
            "headers": dict(e.headers.items()),
            "text": text,
            "text_len": len(text),
        }
    except Exception as e:
        return {
            "ok": False,
            "status": "ERR",
            "url": url,
            "error": repr(e),
            "text": "",
            "text_len": 0,
        }


def page_check(name: str, path: str) -> dict:
    res = request("GET", path)
    html = res.get("text", "")
    return {
        "name": name,
        "path": path,
        "status": res["status"],
        "css": CSS_RE.findall(html),
        "js": JS_RE.findall(html),
        "has_operator_root": "data-ff-operator-root" in html,
        "has_sponsor_contract": any(
                marker in html
                for marker in (
                    "ffSponsorContract",
                    "data-ff-sponsor-contract",
                    "data-ff-sponsor-contract-script",
                    "sponsor-packages-v1",
                    "data-ff-sponsor-packages",
                    "data-ff-sponsor-tier-grid",
                    "data-ff-sponsor-card",
                )
            ),
        "has_product_handoff_css": "ff.product-handoff.css" in html,
        "has_template_leak": "{{" in html or "{%" in html,
        "html_len": len(html),
    }


def signed_webhook_check() -> dict:
    secret = (
        ENV.get("FF_STRIPE_WEBHOOK_SECRET")
        or ENV.get("STRIPE_WEBHOOK_SECRET")
        or ENV.get("STRIPE_WEBHOOK_SIGNING_SECRET")
        or ""
    ).strip()

    if not secret.startswith("whsec_"):
        return {
            "skipped": True,
            "reason": "No whsec_ webhook secret found.",
        }

    payload = {
        "id": "evt_futurefunded_audit",
        "object": "event",
        "api_version": "2025-08-27.basil",
        "created": int(time.time()),
        "type": "payment_intent.created",
        "data": {
            "object": {
                "id": "pi_futurefunded_audit",
                "object": "payment_intent",
                "amount": 100,
                "currency": "usd",
                "metadata": {"audit": "true"},
            }
        },
    }

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    signed_payload = timestamp.encode() + b"." + body
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    res = request(
        "POST",
        "/c/stripe/webhook",
        body=body,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": f"t={timestamp},v1={signature}",
        },
    )

    return {
        "status": res["status"],
        "ok": res["status"] in (200, 204),
        "body_preview": res.get("text", "")[:500],
    }


def checkout_check() -> dict:
    body = json.dumps(
        {
            "amount": 25,
            "email": "audit@example.com",
            "name": "FutureFunded Audit Donor",
        }
    ).encode("utf-8")

    res = request(
        "POST",
        "/c/connect-atx-elite/checkout/session",
        body=body,
        headers={"Content-Type": "application/json"},
    )

    text = res.get("text", "")
    return {
        "status": res["status"],
        "ok": res["status"] == 200,
        "has_stripe_not_configured": "stripe_not_configured" in text
        or "Stripe is not configured" in text,
        "has_checkout_url": "checkout.stripe.com" in text or '"url"' in text,
        "body_preview": text[:700],
    }


def main() -> int:
    token = ""
    tmp = Path("/tmp/ff_operator_token")
    if tmp.exists():
        token = tmp.read_text().strip()
    token = token or ENV.get("FF_OPERATOR_ACCESS_TOKEN", "dev_operator_local")

    pages = [
        page_check("homepage", "/platform/"),
        page_check("campaign", "/c/connect-atx-elite"),
        page_check("login", "/platform/login"),
        page_check("onboarding", "/platform/onboarding"),
        page_check("dashboard", f"/platform/dashboard?operator_token={urllib.parse.quote(token)}"),
    ]

    report = {
        "base_url": BASE_URL,
        "env": {
            "STRIPE_SECRET_KEY": mask(ENV.get("STRIPE_SECRET_KEY")),
            "FF_STRIPE_WEBHOOK_SECRET": mask(ENV.get("FF_STRIPE_WEBHOOK_SECRET")),
            "STRIPE_WEBHOOK_SECRET": mask(ENV.get("STRIPE_WEBHOOK_SECRET")),
            "STRIPE_WEBHOOK_SIGNING_SECRET": mask(ENV.get("STRIPE_WEBHOOK_SIGNING_SECRET")),
            "FF_OPERATOR_ACCESS_TOKEN": mask(ENV.get("FF_OPERATOR_ACCESS_TOKEN")),
            "/tmp/ff_operator_token": mask(token),
        },
        "pages": pages,
        "checkout": checkout_check(),
        "webhook": signed_webhook_check(),
    }

    failures = []

    for p in pages:
        if p["status"] != 200:
            failures.append(f"{p['name']} returned {p['status']}")
        if p["has_template_leak"]:
            failures.append(f"{p['name']} has template leak")
        if p["name"] == "campaign" and not p["has_sponsor_contract"]:
            failures.append("campaign missing sponsor contract script")
        if p["name"] == "campaign" and p["has_product_handoff_css"]:
            failures.append("campaign still loads ff.product-handoff.css")
        if p["name"] == "dashboard" and not p["has_operator_root"]:
            failures.append("dashboard missing data-ff-operator-root")

    if not report["checkout"]["ok"]:
        failures.append(f"checkout failed with {report['checkout']['status']}")

    if not report["webhook"].get("ok"):
        failures.append(f"webhook failed/skipped: {report['webhook']}")

    report["failures"] = failures

    json_path = OUT / "ff_live_runtime_audit.json"
    md_path = OUT / "ff_live_runtime_audit.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Live Runtime Audit")
    lines.append("")
    lines.append(f"Base URL: `{BASE_URL}`")
    lines.append("")
    lines.append(f"Failures: **{len(failures)}**")
    lines.append("")
    if failures:
        for f in failures:
            lines.append(f"- ❌ {f}")
    else:
        lines.append("- ✅ Live runtime checks passed")
    lines.append("")
    lines.append("## Pages")
    lines.append("")
    lines.append(
        "| Page | Status | CSS | JS | Sponsor contract | Operator root | Product handoff CSS |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for p in pages:
        lines.append(
            f"| {p['name']} | {p['status']} | {len(p['css'])} | {len(p['js'])} | "
            f"{p['has_sponsor_contract']} | {p['has_operator_root']} | {p['has_product_handoff_css']} |"
        )
    lines.append("")
    lines.append("## Checkout")
    lines.append("")
    lines.append(f"- Status: `{report['checkout']['status']}`")
    lines.append(f"- OK: `{report['checkout']['ok']}`")
    lines.append(f"- Stripe not configured: `{report['checkout']['has_stripe_not_configured']}`")
    lines.append("")
    lines.append("## Webhook")
    lines.append("")
    lines.append(f"- Status: `{report['webhook'].get('status', 'skipped')}`")
    lines.append(f"- OK: `{report['webhook'].get('ok', False)}`")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("\nFutureFunded live runtime audit")
    print("===============================")
    print(f"Failures: {len(failures)}")
    for f in failures:
        print(f"❌ {f}")
    if not failures:
        print("✅ Live runtime checks passed")
    print(f"\nMarkdown: {md_path}")
    print(f"JSON:     {json_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

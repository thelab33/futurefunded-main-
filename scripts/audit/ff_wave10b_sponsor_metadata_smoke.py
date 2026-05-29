#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(".").resolve()
OUT = ROOT / "audit_outputs"
OUT.mkdir(exist_ok=True)

URL = "http://127.0.0.1:5000/c/connect-atx-elite/checkout/session"

payload = {
    "flow": "sponsor",
    "kind": "sponsor",
    "source": "wave10b-metadata-smoke",
    "amount": 1500,
    "amount_cents": 150000,
    "frequency": "once",
    "sponsor_intake": {
        "business_name": "Wave 10B Test Sponsor",
        "email": "sponsor-ops@example.com",
        "recognition_name": "Wave 10B Community Champion",
        "website": "https://example.com",
        "package": "season",
        "package_label": "Season Sponsor",
        "package_amount": "1500",
        "package_amount_cents": "150000",
        "recognition_note": "Please review before publishing.",
    },
}

def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as res:
        body = res.read().decode("utf-8", errors="replace")
        return {"status": res.status, "json": json.loads(body)}

def main() -> int:
    result = post_json(URL, payload)
    data = result["json"]
    session_id = data.get("id") or data.get("sessionId") or ""

    queue_file = ROOT / "instance" / "sponsor-review-queue" / f"{session_id}.json"
    queue_data = {}
    if queue_file.exists():
        queue_data = json.loads(queue_file.read_text(encoding="utf-8"))

    sponsor = queue_data.get("sponsor") or {}

    checks = {
        "checkout_http_200": result["status"] == 200,
        "session_created": str(session_id).startswith("cs_"),
        "checkout_url_present": "checkout.stripe.com" in str(data.get("url", "")),
        "queue_file_created": queue_file.exists(),
        "business_name_recorded": sponsor.get("business_name") == "Wave 10B Test Sponsor",
        "contact_email_recorded": sponsor.get("contact_email") == "sponsor-ops@example.com",
        "recognition_name_recorded": sponsor.get("recognition_name") == "Wave 10B Community Champion",
        "package_recorded": sponsor.get("package") == "season",
        "amount_cents_recorded": sponsor.get("package_amount_cents") == "150000",
        "review_gated": (queue_data.get("review") or {}).get("review_required") is True,
        "public_recognition_not_auto_allowed": (queue_data.get("review") or {}).get("public_recognition_allowed") is False,
    }

    passed = all(checks.values())

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "passed": passed,
        "checks": checks,
        "session_id": session_id,
        "queue_file": str(queue_file),
        "queue_preview": queue_data,
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT / f"ff_wave10b_sponsor_metadata_smoke_{stamp}.json"
    md_path = OUT / f"ff_wave10b_sponsor_metadata_smoke_{stamp}.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# FutureFunded Wave 10B Sponsor Metadata Smoke",
        "",
        f"- **Generated:** `{report['generated_at']}`",
        f"- **Status:** {'✅ PASS' if passed else '❌ REVIEW'}",
        f"- **Session:** `{session_id}`",
        f"- **Queue file:** `{queue_file}`",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]

    for k, v in checks.items():
        lines.append(f"| `{k}` | {'✅' if v else '❌'} |")

    lines += [
        "",
        "## Sponsor queue preview",
        "",
        "```json",
        json.dumps(queue_data.get("sponsor") or {}, indent=2),
        "```",
    ]

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 10B sponsor metadata smoke: {md_path}")
    print(f"JSON: {json_path}")
    print(f"Status: {'PASS' if passed else 'REVIEW'}")
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())

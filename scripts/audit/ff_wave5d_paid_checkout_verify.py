#!/usr/bin/env python3
"""
FutureFunded • Wave 5D Paid Checkout Verify

Use after completing a Stripe test checkout in the browser.

It verifies:
- session-status responds
- paid/payment_status fields are visible
- ledger result is present
- lifecycle ledger is present
- preview spool contains lifecycle messages

Usage:
  python scripts/audit/ff_wave5d_paid_checkout_verify.py cs_test_...
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


def get_json(path: str) -> dict:
    url = BASE + path
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,*/*",
            "User-Agent": "FutureFundedWave5DPaidCheckoutVerify/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except Exception:
                data = {"raw": raw[:1200]}
            return {"status": resp.status, "url": url, "json": data, "ok": True}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw": raw[:1200]}
        return {"status": exc.code, "url": url, "json": data, "ok": False}


def latest_spool(limit: int = 12) -> list[str]:
    spool = Path("instance/email-spool")
    if not spool.exists():
        return []
    return [str(p) for p in sorted(spool.glob("*.json"))[-limit:]]


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/audit/ff_wave5d_paid_checkout_verify.py cs_test_...")
        return 2

    session_id = sys.argv[1].strip()

    # Accept either raw cs_test_... or shell-style SESSION_ID=cs_test_...
    if session_id.startswith("SESSION_ID="):
        session_id = session_id.split("=", 1)[1].strip()

    # If someone accidentally pastes a URL, try to recover the cs_test id.
    if "cs_test_" in session_id:
        session_id = "cs_test_" + session_id.split("cs_test_", 1)[1].split("#", 1)[0].split("&", 1)[0].split("?", 1)[0].strip()

    qs = urllib.parse.urlencode({"session_id": session_id})
    status = get_json(f"/c/{SLUG}/checkout/session-status?{qs}")

    data = status["json"] if isinstance(status.get("json"), dict) else {}

    lifecycle_ledger = Path("instance/lifecycle-events.json")
    lifecycle_data = {}
    if lifecycle_ledger.exists():
        try:
            lifecycle_data = json.loads(lifecycle_ledger.read_text(encoding="utf-8"))
        except Exception:
            lifecycle_data = {"error": "could_not_parse_lifecycle_ledger"}

    checks = {
        "session_status_200": status["status"] == 200,
        "session_id_matches": data.get("sessionId") == session_id or data.get("session_id") == session_id,
        "has_payment_status": "payment_status" in data,
        "paid_or_complete": bool(data.get("paid")) or str(data.get("status", "")).lower() == "complete",
        "has_ledger_result": "ledger" in data,
        "lifecycle_ledger_exists": lifecycle_ledger.exists(),
        "preview_spool_has_messages": bool(latest_spool()),
    }

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "passed": all(checks.values()),
        "checks": checks,
        "session_status": status,
        "lifecycle_ledger_path": str(lifecycle_ledger),
        "lifecycle_ledger_event_count": len((lifecycle_data.get("events") or {})) if isinstance(lifecycle_data, dict) else 0,
        "latest_preview_spool": latest_spool(),
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT_DIR / f"ff_wave5d_paid_checkout_verify_{stamp}.json"
    md_path = OUT_DIR / f"ff_wave5d_paid_checkout_verify_{stamp}.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 5D Paid Checkout Verify")
    lines.append("")
    lines.append(f"- **Generated:** `{report['generated_at']}`")
    lines.append(f"- **Session:** `{session_id}`")
    lines.append(f"- **Passed:** `{report['passed']}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Result |")
    lines.append("| --- | --- |")
    for key, value in checks.items():
        lines.append(f"| `{key}` | {'✅' if value else '❌'} |")
    lines.append("")
    lines.append("## Session status fields")
    lines.append("")
    lines.append("```json")
    preview = {
        "status": data.get("status"),
        "payment_status": data.get("payment_status"),
        "paid": data.get("paid"),
        "verified": data.get("verified"),
        "flow": data.get("flow"),
        "amount_display": data.get("amount_display"),
        "campaign_slug": data.get("campaign_slug"),
        "ledger": data.get("ledger"),
    }
    lines.append(json.dumps(preview, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Latest preview spool")
    lines.append("")
    for item in report["latest_preview_spool"]:
        lines.append(f"- `{item}`")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 5D paid checkout verify report: {md_path}")
    print(f"JSON: {json_path}")
    print(f"Passed: {report['passed']}")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

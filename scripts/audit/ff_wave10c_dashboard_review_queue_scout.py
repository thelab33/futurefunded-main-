#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ROOT = Path(".").resolve()
OUT = ROOT / "audit_outputs"
OUT.mkdir(exist_ok=True)

BASE_URL = "http://127.0.0.1:5000/platform/dashboard"

def read_token() -> str:
    env_token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token
    token_file = Path("/tmp/ff_operator_token")
    if token_file.exists():
        return token_file.read_text(encoding="utf-8", errors="replace").strip()
    return ""

def get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")

def candidate_urls() -> list[tuple[str, str]]:
    urls = [("plain", BASE_URL + "?qa=wave10c")]
    token = read_token()
    if token:
        for key in [
            "operator_token",
            "token",
            "access_token",
            "ff_operator_token",
            "operator",
            "auth_token",
        ]:
            qs = urllib.parse.urlencode({key: token, "qa": "wave10c"})
            urls.append((key, BASE_URL + "?" + qs))
    return urls

def main() -> int:
    queue_dir = ROOT / "instance" / "sponsor-review-queue"
    queue_files = sorted(queue_dir.glob("*.json")) if queue_dir.exists() else []

    attempts = []
    best = {"label": "none", "status": 0, "html": ""}

    for label, url in candidate_urls():
        status, html = get(url)
        attempts.append({
            "label": label,
            "status": status,
            "has_dashboard": "data-ff-dashboard-root" in html or "Operator dashboard" in html,
            "has_queue": "data-ff-sponsor-review-queue" in html,
            "has_test_sponsor": "Wave 10B Test Sponsor" in html,
            "length": len(html),
        })

        if "data-ff-sponsor-review-queue" in html:
            best = {"label": label, "status": status, "html": html}
            break

        if len(html) > len(best["html"]):
            best = {"label": label, "status": status, "html": html}

    html = best["html"]
    status = best["status"]

    checks = {
        "dashboard_status_ok": status in (200, 403),
        "queue_files_exist": bool(queue_files),
        "review_queue_rendered": "data-ff-sponsor-review-queue" in html,
        "pending_heading_present": "Pending sponsor recognition" in html,
        "business_name_rendered": "Wave 10B Test Sponsor" in html,
        "recognition_name_rendered": "Wave 10B Community Champion" in html,
        "review_cta_present": "Review sponsor" in html,
        "campaign_sponsor_cta_present": "View campaign sponsor section" in html,
        "review_gated_language_present": "review" in html.lower() and "public recognition" in html.lower(),
    }

    passed = all(checks.values())

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "passed": passed,
        "http_status": status,
        "winning_url_label": best["label"],
        "checks": checks,
        "queue_file_count": len(queue_files),
        "attempts": attempts,
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT / f"ff_wave10c_dashboard_review_queue_scout_{stamp}.json"
    md_path = OUT / f"ff_wave10c_dashboard_review_queue_scout_{stamp}.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# FutureFunded Wave 10C Dashboard Review Queue Scout",
        "",
        f"- **Generated:** `{report['generated_at']}`",
        f"- **Status:** {'✅ PASS' if passed else '❌ REVIEW'}",
        f"- **HTTP:** `{status}`",
        f"- **Winning URL label:** `{best['label']}`",
        f"- **Queue files:** `{len(queue_files)}`",
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
        "## URL attempts",
        "",
        "| Label | HTTP | Dashboard | Queue | Test sponsor | Length |",
        "| --- | ---: | --- | --- | --- | ---: |",
    ]

    for attempt in attempts:
        lines.append(
            f"| `{attempt['label']}` | {attempt['status']} | "
            f"{'✅' if attempt['has_dashboard'] else '❌'} | "
            f"{'✅' if attempt['has_queue'] else '❌'} | "
            f"{'✅' if attempt['has_test_sponsor'] else '❌'} | "
            f"{attempt['length']} |"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 10C dashboard review queue scout: {md_path}")
    print(f"JSON: {json_path}")
    print(f"Status: {'PASS' if passed else 'REVIEW'}")
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())

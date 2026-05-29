#!/usr/bin/env python3
"""
FutureFunded • Wave 2D Lifecycle Provider Readiness

Checks whether donor/sponsor/operator lifecycle messaging is:
- importable
- configured
- dry-run safe
- SMTP-ready
- idempotency-protected
- preview-spooling correctly

Default is read-mostly and safe. It does not send live email.
Use --drill to generate preview-spool messages.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "audit_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


ENV_KEYS = [
    "FF_EMAIL_DRY_RUN",
    "FF_EMAIL_FROM",
    "FF_EMAIL_REPLY_TO",
    "FF_SMTP_HOST",
    "FF_SMTP_PORT",
    "FF_SMTP_USERNAME",
    "FF_SMTP_PASSWORD",
    "FF_SMTP_USE_TLS",
    "FF_EMAIL_PREVIEW_DIR",
    "FF_LIFECYCLE_LEDGER_PATH",
]


def masked_env() -> dict[str, str]:
    result = {}
    for key in ENV_KEYS:
        value = os.getenv(key, "")
        if key in {"FF_SMTP_PASSWORD", "FF_SMTP_USERNAME"} and value:
            result[key] = "***"
        else:
            result[key] = value
    return result


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def latest_files(path: Path, pattern: str, limit: int = 10) -> list[str]:
    """
    Return latest files safely whether `path` is relative or absolute.

    The previous version crashed when preview spool paths were relative
    because Path.relative_to(ROOT) requires both paths to share the same
    absolute root.
    """
    path = path if path.is_absolute() else (ROOT / path)
    path = path.resolve()

    if not path.exists():
        return []

    results = []
    for item in sorted(path.glob(pattern))[-limit:]:
        item = item.resolve()
        try:
            results.append(str(item.relative_to(ROOT)))
        except ValueError:
            results.append(str(item))
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drill", action="store_true", help="Generate preview-spool lifecycle messages.")
    args = parser.parse_args()

    checks = []
    warnings = []
    failures = []

    required_files = [
        "apps/web/app/services/ff_lifecycle_messages.py",
        "apps/web/app/services/ff_transactional_email.py",
        "apps/web/app/services/ff_lifecycle_dispatch.py",
        "apps/web/app/services/ff_lifecycle_once.py",
        "scripts/audit/ff_lifecycle_message_drill.py",
        "scripts/audit/ff_lifecycle_dispatch_drill.py",
    ]

    for file in required_files:
        ok = exists(file)
        checks.append({"check": f"file exists: {file}", "ok": ok})
        if not ok:
            failures.append(f"Missing required lifecycle file: {file}")

    try:
        from apps.web.app.services.ff_transactional_email import provider_status
        from apps.web.app.services.ff_lifecycle_messages import render_all_samples, sample_payload
        from apps.web.app.services.ff_lifecycle_dispatch import (
            dispatch_donation_lifecycle,
            dispatch_sponsor_lifecycle,
        )
        from apps.web.app.services.ff_lifecycle_once import lifecycle_key

        imports_ok = True
    except Exception as exc:
        imports_ok = False
        failures.append(f"Lifecycle imports failed: {type(exc).__name__}: {exc}")

    checks.append({"check": "lifecycle imports", "ok": imports_ok})

    provider = {}
    sample_summary = []
    dispatch_preview = None

    if imports_ok:
        provider = provider_status()

        smtp_ready = bool(provider.get("smtp_ready"))
        dry_run = bool(provider.get("dry_run"))

        checks.append({"check": "SMTP provider ready", "ok": smtp_ready})
        checks.append({"check": "dry-run mode enabled", "ok": dry_run})

        if not smtp_ready:
            warnings.append("SMTP is not configured yet. Lifecycle messages will preview-spool, not send live email.")

        if dry_run:
            warnings.append("FF_EMAIL_DRY_RUN is enabled or defaulting on. This is safe for QA, but production delivery needs FF_EMAIL_DRY_RUN=0.")

        payload = sample_payload()
        messages = render_all_samples(payload)
        sample_summary = [
            {
                "category": m.category,
                "to": m.to_email,
                "subject": m.subject,
                "has_text": bool(m.text_body.strip()),
                "has_html": bool(m.html_body.strip()),
            }
            for m in messages
        ]

        if len(messages) != 4:
            failures.append(f"Expected 4 sample lifecycle messages; found {len(messages)}")

        for m in messages:
            if not m.to_email:
                warnings.append(f"{m.category} has no recipient in sample payload.")
            if not m.subject:
                failures.append(f"{m.category} has no subject.")
            if not m.text_body or not m.html_body:
                failures.append(f"{m.category} missing text or HTML body.")

        donation_key = lifecycle_key("donation", "cs_test_provider_readiness", payload)
        sponsor_key = lifecycle_key("sponsor", "cs_test_provider_readiness", payload)
        checks.append({"check": "idempotency key donation", "ok": donation_key.startswith("donation:")})
        checks.append({"check": "idempotency key sponsor", "ok": sponsor_key.startswith("sponsor:")})

        if args.drill:
            dispatch_preview = {
                "donation": dispatch_donation_lifecycle(payload),
                "sponsor": dispatch_sponsor_lifecycle(payload),
            }

    spool_dir = Path(os.getenv("FF_EMAIL_PREVIEW_DIR", "instance/email-spool"))
    ledger_path = Path(os.getenv("FF_LIFECYCLE_LEDGER_PATH", "instance/lifecycle-events.json"))

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "fail" if failures else ("warn" if warnings else "pass"),
        "checks": checks,
        "warnings": warnings,
        "failures": failures,
        "provider": provider,
        "env": masked_env(),
        "sample_messages": sample_summary,
        "dispatch_preview": dispatch_preview,
        "preview_spool": {
            "dir": str(spool_dir),
            "exists": spool_dir.exists(),
            "latest": latest_files(spool_dir, "*.json"),
        },
        "idempotency_ledger": {
            "path": str(ledger_path),
            "exists": ledger_path.exists(),
        },
        "production_next_steps": [
            "Choose SMTP provider: Postmark, SendGrid, Mailgun, SES, or another SMTP-compatible provider.",
            "Set FF_EMAIL_FROM and FF_EMAIL_REPLY_TO.",
            "Set FF_SMTP_HOST, FF_SMTP_PORT, FF_SMTP_USERNAME, FF_SMTP_PASSWORD, FF_SMTP_USE_TLS.",
            "Set FF_EMAIL_DRY_RUN=0 only after a successful live SMTP test.",
            "Keep lifecycle idempotency ledger enabled to avoid duplicate donor/sponsor emails.",
        ],
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT_DIR / f"ff_wave2d_lifecycle_provider_readiness_{stamp}.json"
    md_path = OUT_DIR / f"ff_wave2d_lifecycle_provider_readiness_{stamp}.md"

    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 2D Lifecycle Provider Readiness")
    lines.append("")
    lines.append(f"- **Generated:** `{result['generated_at']}`")
    lines.append(f"- **Status:** `{result['status']}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Result |")
    lines.append("| --- | --- |")
    for check in checks:
        lines.append(f"| {check['check']} | {'✅' if check['ok'] else '❌'} |")
    lines.append("")

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for item in warnings:
            lines.append(f"- ⚠️ {item}")
        lines.append("")

    if failures:
        lines.append("## Failures")
        lines.append("")
        for item in failures:
            lines.append(f"- ❌ {item}")
        lines.append("")

    lines.append("## Provider")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(provider, indent=2))
    lines.append("```")
    lines.append("")

    lines.append("## Sample Messages")
    lines.append("")
    lines.append("| Category | To | Subject | Text | HTML |")
    lines.append("| --- | --- | --- | --- | --- |")
    for m in sample_summary:
        lines.append(f"| {m['category']} | `{m['to']}` | {m['subject']} | {'✅' if m['has_text'] else '❌'} | {'✅' if m['has_html'] else '❌'} |")
    lines.append("")

    lines.append("## Preview Spool")
    lines.append("")
    lines.append(f"- **Directory:** `{result['preview_spool']['dir']}`")
    lines.append(f"- **Exists:** `{result['preview_spool']['exists']}`")
    for item in result["preview_spool"]["latest"]:
        lines.append(f"- `{item}`")
    lines.append("")

    lines.append("## Production Next Steps")
    lines.append("")
    for item in result["production_next_steps"]:
        lines.append(f"- {item}")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Lifecycle provider readiness report: {md_path}")
    print(f"JSON: {json_path}")
    print(f"Status: {result['status']}")

    if warnings:
        print("")
        print("Warnings:")
        for item in warnings:
            print(f"  ⚠️ {item}")

    if failures:
        print("")
        print("Failures:")
        for item in failures:
            print(f"  ❌ {item}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

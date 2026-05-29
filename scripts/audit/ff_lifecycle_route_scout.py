#!/usr/bin/env python3
"""
FutureFunded lifecycle route integration scout.

Read-only. Finds likely route insertion points for lifecycle dispatch:
- Stripe checkout/session status
- Stripe webhook
- PayPal capture
- offline donation
- sponsor lead flow
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re


ROOT = Path(".").resolve()
OUT_DIR = ROOT / "audit_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    ROOT / "apps/web/app/blueprints/campaign/routes.py",
    ROOT / "apps/web/app/blueprints/sponsors/routes.py",
    ROOT / "apps/api/app/routers/payments.py",
    ROOT / "apps/api/app/routers/sponsors.py",
]

PATTERNS = {
    "Stripe checkout/session create": [
        r"checkout/session",
        r"checkout\.Session",
        r"stripe\.checkout",
    ],
    "Stripe session-status paid confirmation": [
        r"session-status",
        r"payment_status",
        r"checkout_status",
        r"\bpaid\b",
    ],
    "Stripe webhook paid/completed": [
        r"webhook",
        r"checkout\.session\.completed",
        r"payment_intent",
        r"stripe\.Webhook",
    ],
    "PayPal capture": [
        r"paypal",
        r"capture",
        r"order_id",
    ],
    "Offline donation ledger": [
        r"offline-donation",
        r"ledger/offline",
        r"offline",
    ],
    "Sponsor lead": [
        r"sponsor",
        r"lead",
        r"business_name",
        r"sponsor_email",
    ],
}


def line_no(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def window(lines: list[str], line: int, radius: int = 10) -> str:
    start = max(1, line - radius)
    end = min(len(lines), line + radius)
    out = []
    for idx in range(start, end + 1):
        out.append(f"{idx:>5}: {lines[idx - 1]}")
    return "\n".join(out)


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = OUT_DIR / f"ff_lifecycle_route_scout_{stamp}.md"

    lines_out = []
    lines_out.append("# FutureFunded Lifecycle Route Scout")
    lines_out.append("")
    lines_out.append(f"- **Generated:** `{datetime.now().isoformat(timespec='seconds')}`")
    lines_out.append("")
    lines_out.append("## Integration goal")
    lines_out.append("")
    lines_out.append("Wire these safe dispatchers after confirmed events:")
    lines_out.append("")
    lines_out.append("```python")
    lines_out.append("from apps.web.app.services.ff_lifecycle_dispatch import dispatch_donation_lifecycle, dispatch_sponsor_lifecycle")
    lines_out.append("from apps.web.app.services.ff_lifecycle_once import dispatch_once")
    lines_out.append("```")
    lines_out.append("")
    lines_out.append("Use `dispatch_once(...)` so duplicate webhooks/status polls do not duplicate messages.")
    lines_out.append("")

    for target in TARGETS:
        rel = target.relative_to(ROOT)
        lines_out.append(f"## `{rel}`")
        lines_out.append("")

        if not target.exists():
            lines_out.append("_Missing file._")
            lines_out.append("")
            continue

        text = target.read_text(encoding="utf-8", errors="replace")
        text_lines = text.splitlines()

        for label, patterns in PATTERNS.items():
            hits = []
            for pattern in patterns:
                for m in re.finditer(pattern, text, flags=re.I):
                    hits.append((line_no(text, m.start()), pattern))

            # Deduplicate nearby lines.
            deduped = []
            seen_ranges = []
            for line, pattern in sorted(hits):
                if any(abs(line - seen) <= 6 for seen in seen_ranges):
                    continue
                seen_ranges.append(line)
                deduped.append((line, pattern))

            if not deduped:
                continue

            lines_out.append(f"### {label}")
            lines_out.append("")
            for line, pattern in deduped[:6]:
                lines_out.append(f"Candidate around line `{line}` via pattern `{pattern}`:")
                lines_out.append("")
                lines_out.append("```text")
                lines_out.append(window(text_lines, line, radius=8))
                lines_out.append("```")
                lines_out.append("")

    out.write_text("\n".join(lines_out), encoding="utf-8")
    print(f"✅ Lifecycle route scout written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

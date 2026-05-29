#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from pathlib import Path

ROOT = Path.cwd()

TARGETS = [
    ROOT / "apps/web/app/templates/campaign/index.html",
    ROOT / "apps/web/app/templates/campaign_premium.html",
]

BUTTON_RE = re.compile(
    r"<button\b(?=[^>]*data-ff-amount-button=[\"']impact[\"'])(?P<attrs>[^>]*)>",
    re.IGNORECASE | re.DOTALL,
)

AMOUNT_RE = re.compile(
    r"data-ff-(?:donation-amount|checkout-amount|amount)=[\"'](?P<amount>[^\"']+)[\"']",
    re.IGNORECASE,
)

MARKER = "hoi-6d1-impact-aria-labels"


def label_for(attrs: str) -> str:
    match = AMOUNT_RE.search(attrs)
    if not match:
        return "Donate selected amount"

    amount = match.group("amount").strip()

    # Static rendered/template amount.
    if re.fullmatch(r"\d+(?:\.\d+)?", amount):
        if amount.endswith(".0"):
            amount = amount[:-2]
        return f"Donate ${amount}"

    # Jinja/dynamic expression fallback.
    if "{{" in amount or "{%" in amount:
        return f"Donate ${{{{ {amount.strip('{} ').strip()} }}}}"

    return f"Donate ${amount}"


def patch_file(path: Path) -> bool:
    if not path.exists():
        return False

    text = path.read_text(errors="ignore")

    if MARKER in text:
        print(f"Already patched: {path}")
        return False

    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed

        full = match.group(0)
        attrs = match.group("attrs")

        if re.search(r"\baria-label\s*=", attrs, re.IGNORECASE):
            return full

        label = label_for(attrs)
        changed = True

        return f'<button aria-label="{label}"{attrs}>'

    new_text = BUTTON_RE.sub(replace, text)

    if not changed:
        print(f"No matching unlabelled impact buttons found: {path}")
        return False

    backup = path.with_suffix(path.suffix + f".bak-hoi6d1-{time.strftime('%Y%m%d%H%M%S')}")
    backup.write_text(text)

    new_text = new_text.rstrip() + f"\n{{# {MARKER} #}}\n"
    path.write_text(new_text)

    print(f"Patched: {path}")
    print(f"Backup:  {backup}")
    return True


changed_any = False
for target in TARGETS:
    changed_any |= patch_file(target)

if not changed_any:
    raise SystemExit("No files changed. Inspect campaign templates for impact donation buttons.")

print("HOI 6D.1 campaign impact aria patch complete.")

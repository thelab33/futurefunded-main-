#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from pathlib import Path

ROOT = Path.cwd()
TPL = ROOT / "apps/web/app/templates/campaign/index.html"
MARKER = "hoi-6m4-chip-amount-loop-static-v1"

def backup(path: Path) -> None:
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak-hoi6m4-{stamp}")
    backup_path.write_text(path.read_text(errors="ignore"))
    print(f"Backup: {backup_path}")

def indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]

if not TPL.exists():
    raise SystemExit(f"Missing template: {TPL}")

text = TPL.read_text(errors="ignore")

if MARKER in text:
    print("Already patched.")
    raise SystemExit(0)

lines = text.splitlines()
out: list[str] = []
converted = 0
i = 0

while i < len(lines):
    line = lines[i]

    if "<button" not in line:
        out.append(line)
        i += 1
        continue

    block: list[str] = [line]

    while i + 1 < len(lines) and "</button>" not in lines[i]:
        i += 1
        block.append(lines[i])

    block_text = "\n".join(block)

    # Exact target: the impact loop amount chip, not the checkout modal amount buttons.
    is_chip_amount_loop = (
        "_chip_amount" in block_text
        and "chip.get('amount')" in block_text
        and "chip.get('label')" in block_text
    )

    if not is_chip_amount_loop:
        out.extend(block)
        i += 1
        continue

    indent = indent_of(block[0])

    span = re.search(r"<span\b[^>]*>.*?</span>", block_text, flags=re.DOTALL)
    strong = re.search(r"<strong\b[^>]*>.*?</strong>", block_text, flags=re.DOTALL)
    para = re.search(r"<p\b[^>]*>.*?</p>", block_text, flags=re.DOTALL)

    pieces = [
        span.group(0).strip() if span else "{{ chip.get('amount') }}",
        strong.group(0).strip() if strong else "<strong>{{ chip.get('label') }}</strong>",
        para.group(0).strip() if para else "<p>{{ chip.get('copy')|default('Shows how this amount helps the season.', true) }}</p>",
    ]

    pieces = [
        re.sub(r"\s+", " ", piece).replace(
            "Tap to donate this amount through secure checkout.",
            "Shows how this amount helps the season."
        )
        for piece in pieces
    ]

    out.append(f"{indent}{{# {MARKER} #}}")
    out.append(
        f"{indent}<article class=\"ff-impactChip ff-impactChip--static\" "
        f"aria-label=\"{{{{ chip.get('amount') }}}} impact: {{{{ chip.get('label') }}}}\">"
    )
    for piece in pieces:
        out.append(f"{indent}  {piece}")
    out.append(f"{indent}</article>")

    converted += 1
    i += 1

new_text = "\n".join(out) + "\n"

required_hooks = [
    "data-ff-open-checkout",
    "data-ff-donate-trigger",
    "data-ff-payment-trigger",
    "data-ff-open-sponsor",
    "data-ff-sponsor-trigger",
    "data-ff-share-trigger",
    "data-ff-qr-trigger",
    "data-ff-mobile-rail",
]

missing = [hook for hook in required_hooks if hook not in new_text]
if missing:
    raise SystemExit(f"Refusing to write; missing required hooks after conversion: {missing}")

if converted < 1:
    print("No _chip_amount loop button converted. Relevant debug lines:")
    for n, ln in enumerate(text.splitlines(), start=1):
        if "_chip_amount" in ln or "chip.get('amount')" in ln or "data-ff-checkout-amount" in ln:
            print(f"{n}: {ln}")
    raise SystemExit("Expected to convert the Jinja impact chip loop, converted 0.")

backup(TPL)
TPL.write_text(new_text)

print(f"Converted Jinja impact chip loop blocks: {converted}")
print(f"Patched: {TPL}")

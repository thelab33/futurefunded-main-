#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path.cwd()
DEFAULT_TEMPLATE = Path("apps/web/app/templates/campaign/index.html")
CSS_ROOT = Path("apps/web/app/static/css")
OUT_ROOT = Path("audit_outputs/campaign-css-bundle")
PROOF_JSON = Path("docs/release-proof/campaign-css-bundle-latest.json")


MODE_HELP = """
linked-all:
  Bundle every unique CSS file linked by campaign/index.html in template order.

campaign-only:
  Bundle linked CSS files except ff.css and ff.checkout.css.

small-safe:
  Bundle only campaign.css + campaign.authority.css when linked or present.
"""


@dataclass
class CssFileReport:
    order: int
    file: str
    path: str
    exists: bool
    included: bool
    reason: str
    lines: int = 0
    bytes: int = 0
    sha256: str = ""
    non_campaign_surface_signals: int = 0
    checkout_signals: int = 0
    campaign_signals: int = 0
    layer_count: int = 0
    important_count: int = 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def unique_in_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def extract_css_links(template_text: str) -> list[str]:
    # Matches Jinja url_for static references like:
    # filename='css/ff.css'
    # filename="css/campaign.unified.css"
    refs = re.findall(r"filename\s*=\s*['\"]css/([^'\"]+\.css)['\"]", template_text)
    return unique_in_order(refs)


def classify_css(name: str, text: str) -> tuple[str, dict[str, int]]:
    non_campaign = len(re.findall(r"ff-platform|ff-dashboard|ff-onboard|ff-login|platform-home", text))
    checkout = len(re.findall(r"ff-checkout|ff-embeddedCheckout|ff-payment|checkout", text, re.I))
    campaign = len(re.findall(r"ff-campaign|campaign|ff-donate|ff-sponsor|ff-momentum", text))
    layer_count = len(re.findall(r"@layer\s+", text))
    important_count = text.count("!important")

    if name == "ff.css":
        reason = "global-system-css"
    elif name == "ff.checkout.css":
        reason = "checkout-safety-css"
    elif non_campaign > 0:
        reason = "mixed-surface-css"
    elif checkout > 0 and "checkout" in name:
        reason = "checkout-css"
    elif campaign > 0:
        reason = "campaign-scoped-css"
    else:
        reason = "unknown-or-minimal-css"

    return reason, {
        "non_campaign_surface_signals": non_campaign,
        "checkout_signals": checkout,
        "campaign_signals": campaign,
        "layer_count": layer_count,
        "important_count": important_count,
    }


def should_include(name: str, mode: str) -> tuple[bool, str]:
    if mode == "linked-all":
        return True, "included by linked-all"

    if mode == "campaign-only":
        if name in {"ff.css", "ff.checkout.css"}:
            return False, "excluded global/checkout foundation"
        return True, "included by campaign-only"

    if mode == "small-safe":
        if name in {"campaign.css", "campaign.authority.css", "campaign.unified.css"}:
            return True, "included by small-safe"
        return False, "excluded by small-safe"

    raise ValueError(f"Unknown mode: {mode}")


def build_bundle(
    template: Path,
    mode: str,
    output_dir: Path,
    allow_missing: bool,
) -> dict:
    if not template.exists():
        raise SystemExit(f"Missing template: {template}")

    template_text = read_text(template)
    linked_css = extract_css_links(template_text)

    # small-safe should work even before/after template link changes.
    if mode == "small-safe":
        for extra in ["campaign.css", "campaign.authority.css", "campaign.unified.css"]:
            if extra not in linked_css and (CSS_ROOT / extra).exists():
                linked_css.append(extra)

    output_dir.mkdir(parents=True, exist_ok=True)

    reports: list[CssFileReport] = []
    bundle_parts: list[str] = []

    header = f"""/*
  FutureFunded Campaign CSS Bundle
  Generated: {datetime.now(timezone.utc).isoformat()}
  Mode: {mode}
  Template: {template}

  IMPORTANT:
  - This is a review/audit bundle, not automatically a production replacement.
  - Do not link this file in production until the cascade is reviewed.
  - Source files are preserved with BEGIN/END markers.
*/

"""
    bundle_parts.append(header)

    missing: list[str] = []

    for index, name in enumerate(linked_css, start=1):
        include, include_reason = should_include(name, mode)
        path = CSS_ROOT / name

        if not path.exists():
            missing.append(name)
            reports.append(CssFileReport(
                order=index,
                file=name,
                path=str(path),
                exists=False,
                included=False,
                reason="missing",
            ))
            continue

        text = read_text(path)
        css_reason, signals = classify_css(name, text)

        report = CssFileReport(
            order=index,
            file=name,
            path=str(path),
            exists=True,
            included=include,
            reason=f"{include_reason}; {css_reason}" if include else f"{include_reason}; {css_reason}",
            lines=text.count("\n") + 1,
            bytes=len(text.encode("utf-8", errors="replace")),
            sha256=sha256_text(text),
            **signals,
        )
        reports.append(report)

        if include:
            bundle_parts.append(
                f"""
/* ==========================================================================
   BEGIN SOURCE {index}: {name}
   Path: {path}
   Reason: {report.reason}
   Lines: {report.lines}
   Bytes: {report.bytes}
   SHA256: {report.sha256}
   ========================================================================== */

{text.rstrip()}

/* ==========================================================================
   END SOURCE {index}: {name}
   ========================================================================== */
"""
            )

    if missing and not allow_missing:
        raise SystemExit(
            "Missing CSS files: "
            + ", ".join(missing)
            + "\nUse --allow-missing only if this is expected."
        )

    bundle_name = f"campaign-css-bundle-{mode}.css"
    bundle_path = output_dir / bundle_name
    bundle_path.write_text("\n".join(bundle_parts).rstrip() + "\n", encoding="utf-8")

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "template": str(template),
        "bundlePath": str(bundle_path),
        "linkedCssInOrder": linked_css,
        "includedCss": [r.file for r in reports if r.included],
        "excludedCss": [r.file for r in reports if not r.included],
        "missingCss": missing,
        "reports": [asdict(r) for r in reports],
    }

    manifest_path = output_dir / f"campaign-css-bundle-{mode}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    PROOF_JSON.parent.mkdir(parents=True, exist_ok=True)
    PROOF_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    latest_dir = OUT_ROOT / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    (latest_dir / bundle_name).write_text(bundle_path.read_text(encoding="utf-8"), encoding="utf-8")
    (latest_dir / f"campaign-css-bundle-{mode}.json").write_text(
        manifest_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect campaign-linked CSS into a single review bundle.",
        epilog=MODE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE),
        help="Campaign template to inspect.",
    )
    parser.add_argument(
        "--mode",
        choices=["linked-all", "campaign-only", "small-safe"],
        default="linked-all",
        help="Bundle mode.",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Output directory. Defaults to audit_outputs/campaign-css-bundle/<timestamp>.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow missing CSS files without failing.",
    )

    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.out) if args.out else OUT_ROOT / stamp

    manifest = build_bundle(
        template=Path(args.template),
        mode=args.mode,
        output_dir=output_dir,
        allow_missing=args.allow_missing,
    )

    print(json.dumps({
        "mode": manifest["mode"],
        "template": manifest["template"],
        "bundlePath": manifest["bundlePath"],
        "proofJson": str(PROOF_JSON),
        "includedCss": manifest["includedCss"],
        "excludedCss": manifest["excludedCss"],
        "missingCss": manifest["missingCss"],
        "latestDir": str(OUT_ROOT / "latest"),
    }, indent=2))


if __name__ == "__main__":
    main()

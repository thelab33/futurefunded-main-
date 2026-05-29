#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
TEMPLATE = ROOT / "apps/web/app/templates/platform/index.html"
CSS_DIR = ROOT / "apps/web/app/static/css"
BUNDLE_NAME = "platform.bundle.css"
BUNDLE_PATH = CSS_DIR / BUNDLE_NAME
PROOF_PATH = ROOT / "docs/release-proof/platform-single-css-bundle-latest.json"

CSS_REF_RE = re.compile(r"filename\s*=\s*['\"]css/([^'\"]+\.css)['\"]")
CSS_LINK_TAG_RE = re.compile(
    r"\n?[ \t]*<link\b(?=[^>]*filename\s*=\s*['\"]css/[^'\"]+\.css['\"])[^>]*>\s*",
    re.S,
)

DEFAULT_SOURCE_STACK = [
    "ff.css",
    "platform-home.css",
    "ff-launch-completion.css",
    "ff-fortune500-final.css",
]


def unique_in_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def main() -> None:
    if not TEMPLATE.exists():
        raise SystemExit(f"Missing template: {TEMPLATE}")

    html = read(TEMPLATE)
    original_html = html

    linked_css = unique_in_order(CSS_REF_RE.findall(html))

    if linked_css == [BUNDLE_NAME]:
        source_css = DEFAULT_SOURCE_STACK
        rerun_mode = True
    else:
        source_css = [name for name in linked_css if name != BUNDLE_NAME]
        rerun_mode = False

    if not source_css:
        raise SystemExit("No homepage CSS files found to bundle.")

    required_sources = {"ff.css", "platform-home.css"}
    missing_required = sorted(required_sources - set(source_css))
    if missing_required:
        raise SystemExit("Refusing to bundle; missing expected homepage CSS refs: " + ", ".join(missing_required))

    source_reports = []
    bundle_parts = [
        f"""/*
  FutureFunded Platform Homepage Single CSS Bundle
  File: apps/web/app/static/css/{BUNDLE_NAME}
  Generated: {datetime.now(timezone.utc).isoformat()}

  Purpose:
  - One homepage stylesheet for /platform/.
  - Preserves original source order.
  - Keeps source files in repo for rollback/provenance.
  - Do not edit manually; regenerate with scripts/release/ff_platform_single_css_bundle.py.

  Source order:
{chr(10).join(f"  - {name}" for name in source_css)}
*/

/* FF_PLATFORM_SINGLE_CSS_BUNDLE_START */
"""
    ]

    missing_files = []

    for index, name in enumerate(source_css, start=1):
        path = CSS_DIR / name
        if not path.exists():
            missing_files.append(name)
            continue

        css = read(path).rstrip()
        source_reports.append({
            "order": index,
            "file": name,
            "path": str(path.relative_to(ROOT)),
            "lines": css.count("\n") + 1,
            "bytes": len(css.encode("utf-8", errors="replace")),
            "sha256": sha(css),
        })

        bundle_parts.append(
            f"""
/* ==========================================================================
   BEGIN SOURCE {index}: {name}
   Path: {path.relative_to(ROOT)}
   ========================================================================== */

{css}

/* ==========================================================================
   END SOURCE {index}: {name}
   ========================================================================== */
"""
        )

    if missing_files:
        raise SystemExit("Missing source CSS files: " + ", ".join(missing_files))

    bundle_parts.append("\n/* FF_PLATFORM_SINGLE_CSS_BUNDLE_END */\n")
    bundle_text = "\n".join(bundle_parts).rstrip() + "\n"
    BUNDLE_PATH.write_text(bundle_text, encoding="utf-8")

    matches = list(CSS_LINK_TAG_RE.finditer(html))
    if not matches:
        raise SystemExit("Could not find homepage CSS link tags to replace.")

    insert_at = matches[0].start()
    html_without_css = CSS_LINK_TAG_RE.sub("", html)

    source_contract = " ".join(source_css)

    bundle_links = f"""
  <!-- FF_PLATFORM_SINGLE_CSS_BUNDLE_SOURCES: {source_contract} -->
  <link
    rel="preload"
    as="style"
    href="{{{{ url_for('static', filename='css/{BUNDLE_NAME}') }}}}?v={{{{ _asset_v|e }}}}"
    data-ff-platform-css-preload="{BUNDLE_NAME}"
    data-ff-platform-bundle-sources="{source_contract}"
  />
  <link
    rel="stylesheet"
    href="{{{{ url_for('static', filename='css/{BUNDLE_NAME}') }}}}?v={{{{ _asset_v|e }}}}"
    data-ff-platform-css="{BUNDLE_NAME}"
    data-ff-platform-bundle-css
    data-ff-platform-bundle-sources="{source_contract}"
  />
"""

    html = html_without_css[:insert_at] + bundle_links + html_without_css[insert_at:]

    required_html = [
        BUNDLE_NAME,
        "FF_PLATFORM_SINGLE_CSS_BUNDLE_SOURCES",
        "ff.css",
        "platform-home.css",
        "ffHomeConfig",
        "data-ff-home-cta",
        "data-ff-home-demo-cta",
        "Launch a premium fundraising page",
    ]

    missing_html = [item for item in required_html if item not in html]
    if missing_html:
        raise SystemExit("Missing required homepage contracts: " + ", ".join(missing_html))

    forbidden_href_refs = [
        "css/ff.css",
        "css/platform-home.css",
        "css/ff-launch-completion.css",
        "css/ff-fortune500-final.css",
    ]
    old_refs = [ref for ref in forbidden_href_refs if ref in html]
    if old_refs:
        raise SystemExit("Old CSS href references still present: " + ", ".join(old_refs))

    if html != original_html:
        TEMPLATE.write_text(html, encoding="utf-8")

    proof = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "rerunMode": rerun_mode,
        "template": str(TEMPLATE.relative_to(ROOT)),
        "bundle": str(BUNDLE_PATH.relative_to(ROOT)),
        "bundleLines": bundle_text.count("\n") + 1,
        "bundleBytes": len(bundle_text.encode("utf-8", errors="replace")),
        "bundleSha256": sha(bundle_text),
        "sourceCss": source_css,
        "sourceReports": source_reports,
        "templateCssLinksAfter": unique_in_order(CSS_REF_RE.findall(html)),
    }

    PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROOF_PATH.write_text(json.dumps(proof, indent=2), encoding="utf-8")

    print(json.dumps({
        "bundle": proof["bundle"],
        "bundleLines": proof["bundleLines"],
        "sourceCss": proof["sourceCss"],
        "templateCssLinksAfter": proof["templateCssLinksAfter"],
        "proof": str(PROOF_PATH.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()

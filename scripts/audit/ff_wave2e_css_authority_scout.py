#!/usr/bin/env python3
"""
FutureFunded • Wave 2E CSS Authority Scout

Read-only.
Maps:
- canonical CSS files
- CSS linked by rendered pages
- CSS linked by templates
- file sizes
- suspicious patch/rescue/stability markers
- likely unused CSS files
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(".").resolve()
OUT_DIR = ROOT / "audit_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSS_DIR = ROOT / "apps/web/app/static/css"

URLS = [
    "http://127.0.0.1:5000/platform",
    "http://127.0.0.1:5000/platform/onboarding",
    "http://127.0.0.1:5000/c/connect-atx-elite",
    "https://getfuturefunded.com/platform/",
    "https://getfuturefunded.com/c/connect-atx-elite",
]

TEMPLATE_ROOTS = [
    ROOT / "apps/web/app/templates",
]

CSS_LINK_RE = re.compile(r"""href=["'](?P<href>[^"']*?/static/css/[^"']+?\.css(?:\?[^"']*)?)["']""", re.I)
CSS_IMPORT_RE = re.compile(r"""@import\s+(?:url\()?["']?(?P<path>[^"')]+\.css)["']?\)?""", re.I)
MARKER_RE = re.compile(r"\b(rescue|emergency|temporary|TODO|FIXME|HACK|deprecated|patch)\b", re.I)


def fetch(url: str) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FutureFundedCSSAuthorityScout/1.0", "Accept": "text/html,*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace"), None
    except Exception as exc:
        return None, "", f"{type(exc).__name__}: {exc}"


def normalize_css_href(href: str) -> str:
    href = href.split("?", 1)[0]
    if "/static/css/" in href:
        return "apps/web/app" + href[href.index("/static/css/"):]
    return href


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def main() -> int:
    css_files = sorted(CSS_DIR.glob("*.css"))
    css_inventory = []

    for path in css_files:
        text = read(path)
        css_inventory.append({
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "lines": text.count("\n") + 1,
            "imports": CSS_IMPORT_RE.findall(text),
            "marker_hits": len(MARKER_RE.findall(text)),
        })

    rendered_links = defaultdict(list)
    fetch_errors = []

    for url in URLS:
        status, html, err = fetch(url)
        if err:
            fetch_errors.append({"url": url, "error": err})
            continue
        for m in CSS_LINK_RE.finditer(html):
            rendered_links[normalize_css_href(m.group("href"))].append(url)

    template_links = defaultdict(list)

    for root in TEMPLATE_ROOTS:
        for path in root.rglob("*"):
            if path.suffix.lower() not in {".html", ".jinja", ".j2"}:
                continue
            text = read(path)
            rel = str(path.relative_to(ROOT))
            for m in CSS_LINK_RE.finditer(text):
                template_links[normalize_css_href(m.group("href"))].append(rel)

    existing = {item["path"] for item in css_inventory}
    rendered = set(rendered_links)
    templated = set(template_links)

    likely_unused = sorted(existing - rendered - templated)
    rendered_not_existing = sorted(rendered - existing)
    templated_not_existing = sorted(templated - existing)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT_DIR / f"ff_wave2e_css_authority_scout_{stamp}.json"
    md_path = OUT_DIR / f"ff_wave2e_css_authority_scout_{stamp}.md"

    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "css_inventory": css_inventory,
        "rendered_links": dict(rendered_links),
        "template_links": dict(template_links),
        "likely_unused": likely_unused,
        "rendered_not_existing": rendered_not_existing,
        "templated_not_existing": templated_not_existing,
        "fetch_errors": fetch_errors,
    }

    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 2E CSS Authority Scout")
    lines.append("")
    lines.append(f"- **Generated:** `{data['generated_at']}`")
    lines.append(f"- **CSS files:** `{len(css_inventory)}`")
    lines.append(f"- **CSS linked by rendered pages:** `{len(rendered)}`")
    lines.append(f"- **Likely unused CSS files:** `{len(likely_unused)}`")
    lines.append("")

    if fetch_errors:
        lines.append("## Fetch errors")
        lines.append("")
        for err in fetch_errors:
            lines.append(f"- `{err['url']}` → {err['error']}")
        lines.append("")

    lines.append("## CSS inventory")
    lines.append("")
    lines.append("| File | KB | Lines | Imports | Marker hits | Rendered? | Templated? |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- | --- |")

    for item in sorted(css_inventory, key=lambda x: x["bytes"], reverse=True):
        path = item["path"]
        lines.append(
            f"| `{path}` | {item['bytes'] / 1024:.1f} | {item['lines']} | "
            f"{len(item['imports'])} | {item['marker_hits']} | "
            f"{'✅' if path in rendered else ''} | {'✅' if path in templated else ''} |"
        )

    lines.append("")
    lines.append("## Rendered CSS links")
    lines.append("")
    for path, urls in sorted(rendered_links.items()):
        lines.append(f"- `{path}`")
        for url in urls:
            lines.append(f"  - `{url}`")
    lines.append("")

    lines.append("## Likely unused CSS")
    lines.append("")
    if likely_unused:
        for path in likely_unused:
            lines.append(f"- `{path}`")
    else:
        lines.append("_None detected._")
    lines.append("")

    lines.append("## Recommended CSS authority target")
    lines.append("")
    lines.append("1. `ff.css` remains the primary design authority.")
    lines.append("2. `ff.checkout.css` remains checkout-specific only.")
    lines.append("3. `platform-home.css` should either stay as a thin platform layer or be merged later.")
    lines.append("4. Any unlinked legacy CSS should be quarantined, not deleted blindly.")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ CSS authority scout: {md_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

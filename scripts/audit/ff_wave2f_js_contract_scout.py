#!/usr/bin/env python3
"""
FutureFunded • Wave 2F JS Contract Scout

Read-only.
Maps:
- rendered ids/classes/data attributes
- JS querySelector/getElementById selectors
- missing selector candidates
- campaign interaction contracts for checkout/share/sponsor
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(".").resolve()
OUT_DIR = ROOT / "audit_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

URLS = [
    "http://127.0.0.1:5000/platform",
    "http://127.0.0.1:5000/c/connect-atx-elite",
    "https://getfuturefunded.com/platform/",
    "https://getfuturefunded.com/c/connect-atx-elite",
]

JS_ROOTS = [
    ROOT / "apps/web/app/static/js",
]

TEMPLATE_ROOTS = [
    ROOT / "apps/web/app/templates",
]

SELECTOR_RE = re.compile(
    r"""(?:querySelector|querySelectorAll)\(\s*["'](?P<selector>[^"']+)["']\s*\)|getElementById\(\s*["'](?P<id>[^"']+)["']\s*\)""",
    re.I,
)

DATA_SELECTOR_RE = re.compile(r"""\[\s*(data-ff-[\w-]+)(?:[~|^$*]?=["'][^"']+["'])?\s*\]""", re.I)


class AttrParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = Counter()
        self.classes = Counter()
        self.data_attrs = Counter()

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): v or "" for k, v in attrs}
        if attrs.get("id"):
            self.ids[attrs["id"]] += 1
        for cls in attrs.get("class", "").split():
            self.classes[cls] += 1
        for key in attrs:
            if key.startswith("data-"):
                self.data_attrs[key] += 1


def fetch(url: str) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FutureFundedJSContractScout/1.0", "Accept": "text/html,*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace"), None
    except Exception as exc:
        return None, "", f"{type(exc).__name__}: {exc}"


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def scan_js():
    selectors = []

    for root in JS_ROOTS:
        for path in root.rglob("*.js"):
            text = read(path)
            rel = str(path.relative_to(ROOT))

            for m in SELECTOR_RE.finditer(text):
                selector = m.group("selector") or f"#{m.group('id')}"
                line = text.count("\n", 0, m.start()) + 1
                selectors.append({"file": rel, "line": line, "selector": selector})

    return selectors


def scan_templates_pool():
    pool = ""
    for root in TEMPLATE_ROOTS:
        for path in root.rglob("*"):
            if path.suffix.lower() in {".html", ".jinja", ".j2"}:
                pool += "\n" + read(path)
    return pool


def selector_exists(selector: str, rendered, template_pool: str) -> bool:
    selector = selector.strip()

    # Complex selectors need human review unless they contain data attrs.
    if selector.startswith("["):
        attrs = DATA_SELECTOR_RE.findall(selector)
        return all(attr.lower() in rendered["data_attrs"] or attr.lower() in template_pool.lower() for attr in attrs)

    if selector.startswith("#") and re.match(r"^#[A-Za-z][\w:-]*$", selector):
        sid = selector[1:]
        return sid in rendered["ids"] or f'id="{sid}"' in template_pool or f"id='{sid}'" in template_pool

    if selector.startswith(".") and re.match(r"^\.[A-Za-z][\w:-]*$", selector):
        cls = selector[1:]
        return cls in rendered["classes"] or cls in template_pool

    attrs = DATA_SELECTOR_RE.findall(selector)
    if attrs:
        return all(attr.lower() in rendered["data_attrs"] or attr.lower() in template_pool.lower() for attr in attrs)

    return True


def main() -> int:
    rendered = {
        "ids": Counter(),
        "classes": Counter(),
        "data_attrs": Counter(),
    }

    fetch_errors = []

    for url in URLS:
        status, html, err = fetch(url)
        if err:
            fetch_errors.append({"url": url, "error": err})
            continue

        parser = AttrParser()
        parser.feed(html)
        rendered["ids"].update(parser.ids)
        rendered["classes"].update(parser.classes)
        rendered["data_attrs"].update(parser.data_attrs)

    selectors = scan_js()
    template_pool = scan_templates_pool()

    missing = []
    for item in selectors:
        if not selector_exists(item["selector"], rendered, template_pool):
            missing.append(item)

    campaign_contracts = [
        "data-ff-open-checkout",
        "data-ff-donate-trigger",
        "data-ff-payment-trigger",
        "data-ff-open-sponsor",
        "data-ff-sponsor-trigger",
        "data-ff-share-trigger",
        "data-ff-qr-trigger",
        "data-ff-close-qr-modal",
        "data-ff-close-embedded-checkout",
        "data-ff-sponsor-submit",
        "data-ff-open-sponsor-checkout",
    ]

    contract_status = {
        key: int(rendered["data_attrs"].get(key, 0))
        for key in campaign_contracts
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT_DIR / f"ff_wave2f_js_contract_scout_{stamp}.json"
    md_path = OUT_DIR / f"ff_wave2f_js_contract_scout_{stamp}.md"

    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "selectors_found": selectors,
        "missing_selector_candidates": missing,
        "contract_status": contract_status,
        "fetch_errors": fetch_errors,
        "top_data_attrs": rendered["data_attrs"].most_common(40),
        "top_ids": rendered["ids"].most_common(40),
    }

    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 2F JS Contract Scout")
    lines.append("")
    lines.append(f"- **Generated:** `{data['generated_at']}`")
    lines.append(f"- **JS selectors found:** `{len(selectors)}`")
    lines.append(f"- **Missing selector candidates:** `{len(missing)}`")
    lines.append("")

    if fetch_errors:
        lines.append("## Fetch errors")
        lines.append("")
        for err in fetch_errors:
            lines.append(f"- `{err['url']}` → {err['error']}")
        lines.append("")

    lines.append("## Campaign interaction contracts")
    lines.append("")
    lines.append("| Contract | Rendered count |")
    lines.append("| --- | ---: |")
    for key, count in contract_status.items():
        lines.append(f"| `{key}` | {count} |")
    lines.append("")

    lines.append("## Missing selector candidates")
    lines.append("")
    if missing:
        lines.append("| File | Line | Selector |")
        lines.append("| --- | ---: | --- |")
        for item in missing:
            lines.append(f"| `{item['file']}` | {item['line']} | `{item['selector']}` |")
    else:
        lines.append("_None detected._")
    lines.append("")

    lines.append("## Top rendered data attributes")
    lines.append("")
    lines.append("| Data attr | Count |")
    lines.append("| --- | ---: |")
    for key, count in rendered["data_attrs"].most_common(40):
        lines.append(f"| `{key}` | {count} |")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ JS contract scout: {md_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
FutureFunded • Wave 2B CTA Hierarchy Scout

Read-only.
Finds repeated campaign CTAs in rendered HTML and source templates so we can
tighten Donate / Sponsor / Share hierarchy without guessing.
"""

from __future__ import annotations

import html
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
    "http://127.0.0.1:5000/c/connect-atx-elite",
    "https://getfuturefunded.com/c/connect-atx-elite",
]

SOURCE_FILES = [
    ROOT / "apps/web/app/templates/campaign_premium.html",
    ROOT / "apps/web/app/templates/campaign/index.html",
    ROOT / "apps/web/app/templates/campaign/_checkout_sheet.html",
    ROOT / "apps/web/app/templates/campaign/_modals.html",
    ROOT / "apps/web/app/templates/campaign/_public_sponsor_recognition.html",
    ROOT / "apps/web/app/templates/_base/campaign_base.html",
]

CTA_WORDS = re.compile(r"\b(donate|sponsor|share|checkout|give|support|partner)\b", re.I)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


class CTAParser(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.stack = []
        self.ctas = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = {k.lower(): v or "" for k, v in attrs}
        if tag in {"a", "button"}:
            line, _ = self.getpos()
            self.stack.append([tag, attrs, line, []])

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, -1, -1):
            item = self.stack[i]
            if item[0] == tag:
                tag, attrs, line, chunks = item
                text = clean(" ".join(chunks))
                label = text or attrs.get("aria-label") or attrs.get("title") or attrs.get("data-label") or ""
                if CTA_WORDS.search(label + " " + attrs.get("href", "") + " " + attrs.get("class", "")):
                    self.ctas.append({
                        "source": self.source,
                        "tag": tag,
                        "line": line,
                        "label": clean(label),
                        "href": attrs.get("href", ""),
                        "class": attrs.get("class", ""),
                        "id": attrs.get("id", ""),
                        "type": attrs.get("type", ""),
                        "data": {k: v for k, v in attrs.items() if k.startswith("data-")},
                    })
                del self.stack[i]
                break

    def handle_data(self, data):
        for item in self.stack:
            item[3].append(data)


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FutureFundedCTAScout/1.0", "Accept": "text/html,*/*"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace")


def parse_html(source: str, text: str):
    parser = CTAParser(source)
    parser.feed(text)
    return parser.ctas


def line_window(path: Path, line: int, radius: int = 8) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, line - radius)
    end = min(len(lines), line + radius)
    return "\n".join(f"{idx:>5}: {lines[idx - 1]}" for idx in range(start, end + 1))


def source_candidates():
    candidates = []
    for path in SOURCE_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(ROOT))
        for m in re.finditer(r">\s*([^<>]*(?:Donate|Share|Sponsor|Partner|Support|Give|Checkout)[^<>]*)\s*<|aria-label=[\"']([^\"']+)[\"']|data-ff-[\w-]+=[\"']([^\"']+)[\"']", text, re.I):
            snippet = clean(" ".join(g for g in m.groups() if g))
            if CTA_WORDS.search(snippet):
                line = text.count("\n", 0, m.start()) + 1
                candidates.append({
                    "file": rel,
                    "line": line,
                    "snippet": snippet[:220],
                })
    return candidates


def classify_label(label: str) -> str:
    s = label.lower()
    if "donate" in s or "give" in s or "support" in s or "checkout" in s:
        return "Donation path"
    if "sponsor" in s or "partner" in s:
        return "Sponsor path"
    if "share" in s:
        return "Share utility"
    return "Other"


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = OUT_DIR / f"ff_wave2b_cta_hierarchy_scout_{stamp}.md"
    json_out = OUT_DIR / f"ff_wave2b_cta_hierarchy_scout_{stamp}.json"

    rendered = []
    fetch_errors = []

    for url in URLS:
        try:
            text = fetch(url)
            rendered.extend(parse_html(url, text))
        except Exception as exc:
            fetch_errors.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    sources = source_candidates()

    label_counts = Counter(clean(c["label"]).lower() or "[empty]" for c in rendered)
    role_counts = Counter(classify_label(c["label"]) for c in rendered)

    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "rendered_ctas": rendered,
        "source_candidates": sources,
        "fetch_errors": fetch_errors,
        "label_counts": dict(label_counts.most_common()),
        "role_counts": dict(role_counts.most_common()),
    }
    json_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 2B CTA Hierarchy Scout")
    lines.append("")
    lines.append(f"- **Generated:** `{data['generated_at']}`")
    lines.append(f"- **Rendered CTAs found:** `{len(rendered)}`")
    lines.append(f"- **Source candidates found:** `{len(sources)}`")
    lines.append("")

    if fetch_errors:
        lines.append("## Fetch errors")
        lines.append("")
        for err in fetch_errors:
            lines.append(f"- `{err['url']}` → {err['error']}")
        lines.append("")

    lines.append("## Rendered CTA role counts")
    lines.append("")
    lines.append("| Role | Count |")
    lines.append("| --- | ---: |")
    for role, count in role_counts.most_common():
        lines.append(f"| {role} | {count} |")
    lines.append("")

    lines.append("## Rendered CTA label counts")
    lines.append("")
    lines.append("| Label | Count |")
    lines.append("| --- | ---: |")
    for label, count in label_counts.most_common():
        lines.append(f"| `{label}` | {count} |")
    lines.append("")

    lines.append("## Rendered CTA inventory")
    lines.append("")
    lines.append("| # | Source | Tag | Label | Href | Class | Data attrs |")
    lines.append("| ---: | --- | --- | --- | --- | --- | --- |")
    for idx, cta in enumerate(rendered, start=1):
        source = cta["source"].replace("|", "\\|")
        label = cta["label"].replace("|", "\\|")
        href = cta["href"].replace("|", "\\|")
        cls = cta["class"].replace("|", "\\|")[:120]
        data_attrs = json.dumps(cta["data"], ensure_ascii=False).replace("|", "\\|")
        lines.append(f"| {idx} | `{source}` | `{cta['tag']}` | {label} | `{href}` | `{cls}` | `{data_attrs}` |")
    lines.append("")

    lines.append("## Source candidates")
    lines.append("")
    lines.append("| # | File | Line | Snippet |")
    lines.append("| ---: | --- | ---: | --- |")
    for idx, item in enumerate(sources, start=1):
        snippet = item["snippet"].replace("|", "\\|")
        lines.append(f"| {idx} | `{item['file']}` | {item['line']} | {snippet} |")
    lines.append("")

    lines.append("## Recommended CTA hierarchy")
    lines.append("")
    lines.append("1. **Primary conversion:** keep Donate as the dominant action in the hero/sticky checkout zone.")
    lines.append("2. **Sponsor conversion:** keep Sponsor only in the hero secondary action and sponsor package section.")
    lines.append("3. **Share utility:** demote repeated Share buttons into one utility action near QR/share tools or sticky utility rail.")
    lines.append("4. **Avoid identical labels:** use contextual labels like `Copy campaign link`, `Send to a parent`, or `Share campaign` only once.")
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ CTA hierarchy scout written: {out}")
    print(f"JSON: {json_out}")
    print("")
    print("Top labels:")
    for label, count in label_counts.most_common(10):
        print(f"  {count:>2}  {label}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

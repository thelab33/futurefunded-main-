#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path.cwd()

CSS_FILES = [
    Path("apps/web/app/static/css/ff.css"),
    Path("apps/web/app/static/css/ff.checkout.css"),
    Path("apps/web/app/static/css/campaign.css"),
    Path("apps/web/app/static/css/ff-launch-completion.css"),
    Path("apps/web/app/static/css/ff-campaign-enterprise.css"),
    Path("apps/web/app/static/css/ff-fortune500-final.css"),
    Path("apps/web/app/static/css/ff-campaign-final-compression.css"),
]

TEMPLATE = Path("apps/web/app/templates/campaign/index.html")
OUT_DIR = Path("audit_outputs/campaign-css-inspector")

SELECTOR_RE = re.compile(r"(?P<selectors>[^{}@][^{}]*?)\s*\{", re.S)
COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
MEDIA_RE = re.compile(r"@media[^{]+\{", re.I)
KEYWORDS = [
    ".ff-campaignPage",
    ".ff-campaignMain",
    ".ff-campaignHeader",
    ".ff-campaignHero",
    ".ff-campaignFunnelShell",
    ".ff-campaignHero__grid",
    ".ff-campaignHero__copy",
    "#campaign-hero",
    "padding-top",
    "margin-top",
    "--ff-header-h",
]

def read(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")

def strip_comments(css: str) -> str:
    return COMMENT_RE.sub("", css)

def extract_linked_css(template_text: str) -> list[str]:
    hrefs = re.findall(r"""<link[^>]+href=["']([^"']+\.css[^"']*)["'][^>]*>""", template_text, re.I)
    normalized = []
    for href in hrefs:
        match = re.search(r"css/([^?\"']+\.css)", href)
        if match:
            normalized.append(f"apps/web/app/static/css/{match.group(1)}")
    return normalized

def extract_selectors(css: str) -> list[str]:
    css = strip_comments(css)
    selectors = []
    for match in SELECTOR_RE.finditer(css):
        raw = match.group("selectors").strip()
        if not raw:
            continue
        if raw.startswith("@"):
            continue
        if raw.endswith(")") or raw.endswith(";"):
            continue
        for part in raw.split(","):
            s = " ".join(part.strip().split())
            if s and not s.startswith("@"):
                selectors.append(s)
    return selectors

def find_keyword_lines(path: Path, text: str) -> list[dict]:
    rows = []
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if any(k in line for k in KEYWORDS):
            start = max(1, index - 2)
            end = min(len(lines), index + 2)
            rows.append({
                "line": index,
                "text": line.rstrip(),
                "context": "\n".join(f"{i}: {lines[i-1]}" for i in range(start, end + 1)),
            })
    return rows

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    template_text = read(TEMPLATE)
    linked = extract_linked_css(template_text)

    selector_to_files: dict[str, list[str]] = defaultdict(list)
    file_reports = {}

    for file in CSS_FILES:
        abs_path = ROOT / file
        if not abs_path.exists():
            file_reports[str(file)] = {"exists": False}
            continue

        text = read(file)
        selectors = extract_selectors(text)
        selector_counts = Counter(selectors)

        for selector in sorted(set(selectors)):
            selector_to_files[selector].append(str(file))

        file_reports[str(file)] = {
            "exists": True,
            "bytes": len(text.encode("utf-8")),
            "lines": text.count("\n") + 1,
            "selector_count": len(selectors),
            "unique_selector_count": len(set(selectors)),
            "duplicate_selectors_inside_file": {
                selector: count for selector, count in selector_counts.items() if count > 1
            },
            "top_rhythm_hits": find_keyword_lines(file, text),
        }

    overlapping = {
        selector: files
        for selector, files in selector_to_files.items()
        if len(files) > 1 and any("ff-campaign" in selector or "campaign" in selector or "ff-" in selector for _ in [selector])
    }

    report = {
        "template": str(TEMPLATE),
        "linked_css_in_template_order": linked,
        "unique_linked_css_in_order": list(dict.fromkeys(linked)),
        "expected_css_stack": [str(p) for p in CSS_FILES],
        "files": file_reports,
        "overlapping_selector_count": len(overlapping),
        "overlapping_selectors": dict(sorted(overlapping.items())[:500]),
    }

    json_path = OUT_DIR / "campaign_css_inspector.json"
    md_path = OUT_DIR / "campaign_css_inspector.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = []
    md.append("# FutureFunded Campaign CSS Inspector\n")
    md.append("## Linked CSS in template order\n")
    for item in linked:
        md.append(f"- `{item}`")
    md.append("\n## Unique linked CSS\n")
    for item in list(dict.fromkeys(linked)):
        md.append(f"- `{item}`")

    md.append("\n## File summaries\n")
    for file, info in file_reports.items():
        if not info.get("exists"):
            md.append(f"### `{file}`\n- Missing\n")
            continue
        md.append(f"### `{file}`")
        md.append(f"- Lines: `{info['lines']}`")
        md.append(f"- Bytes: `{info['bytes']}`")
        md.append(f"- Selectors: `{info['selector_count']}`")
        md.append(f"- Unique selectors: `{info['unique_selector_count']}`")
        md.append(f"- Duplicate selectors inside file: `{len(info['duplicate_selectors_inside_file'])}`")
        md.append(f"- Top rhythm hits: `{len(info['top_rhythm_hits'])}`\n")

    md.append("\n## Top rhythm hits by file\n")
    for file, info in file_reports.items():
        hits = info.get("top_rhythm_hits", []) if info.get("exists") else []
        if not hits:
            continue
        md.append(f"### `{file}`")
        for hit in hits[:40]:
            md.append(f"\nLine `{hit['line']}`:")
            md.append("```css")
            md.append(hit["context"])
            md.append("```")

    md.append("\n## Overlapping selectors across files\n")
    md.append(f"Total overlapping selectors: `{len(overlapping)}`\n")
    for selector, files in list(sorted(overlapping.items()))[:180]:
        md.append(f"- `{selector}`")
        for f in files:
            md.append(f"  - `{f}`")

    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print("Campaign CSS inspector complete")
    print(f"MD:   {md_path}")
    print(f"JSON: {json_path}")
    print("\nLinked CSS:")
    for item in linked:
        print(f"- {item}")

if __name__ == "__main__":
    main()

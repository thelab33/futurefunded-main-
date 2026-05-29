#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "audit_outputs" / "copy-risk-locator" / STAMP
LATEST = ROOT / "audit_outputs" / "copy-risk-locator" / "latest"

FILES = [
    "apps/web/app/templates/platform/index.html",
    "apps/web/app/templates/campaign/index.html",
    "apps/web/app/templates/platform/login.html",
    "apps/web/app/templates/platform/onboarding.html",
    "apps/web/app/templates/platform/dashboard.html",
    "apps/web/app/templates/_base/site_base.html",
    "apps/web/app/templates/_base/campaign_base.html",
]

RISK_PATTERNS = {
    "placeholder_copy": re.compile(r"\b(lorem|ipsum|dummy|fake data|sample only|todo|tbd)\b", re.I),
    "weak_launch_copy": re.compile(r"\b(coming soon|under construction|not ready|test campaign|demo only)\b", re.I),
    "unclear_payment_copy": re.compile(r"\b(payment details pending|provider details pending|do not use|disabled)\b", re.I),
    "over_promising_copy": re.compile(r"\b(guaranteed|risk[- ]free|instant payout|no fees ever)\b", re.I),
}

TEXT_ATTRS = ("content", "alt", "aria-label", "title", "placeholder", "value")

TAG_RE = re.compile(r"<[^>]+>")
ATTR_RE = re.compile(
    r"""(?P<name>content|alt|aria-label|title|placeholder|value)\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)""",
    re.I,
)

def strip_jinja_noise(value: str) -> str:
    value = re.sub(r"\{\#.*?\#\}", " ", value)
    value = re.sub(r"\{\%.*?\%\}", " ", value)
    return value

def visible_text_fragments(line: str) -> list[str]:
    fragments: list[str] = []

    # Attribute values donors/operators may hear through screen readers, SEO, or form UX.
    for match in ATTR_RE.finditer(line):
        name = match.group("name").lower()
        value = html.unescape(match.group("value")).strip()

        # Standard technical SEO values are not product copy.
        if name == "content" and "max-image-preview" in value:
            continue

        fragments.append(value)

    # Text nodes outside tags.
    without_tags = TAG_RE.sub(" ", line)
    without_tags = strip_jinja_noise(html.unescape(without_tags)).strip()
    if without_tags:
        fragments.append(without_tags)

    return [f for f in fragments if f]

def context(lines: list[str], idx: int, radius: int = 2) -> list[dict[str, str | int]]:
    start = max(0, idx - radius)
    end = min(len(lines), idx + radius + 1)
    return [{"line": i + 1, "text": lines[i].rstrip()} for i in range(start, end)]

def main() -> int:
    results = []

    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            continue

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

        for idx, line in enumerate(lines):
            fragments = visible_text_fragments(line)
            if not fragments:
                continue

            for fragment in fragments:
                for risk_name, rx in RISK_PATTERNS.items():
                    if rx.search(fragment):
                        results.append({
                            "file": rel,
                            "line": idx + 1,
                            "risk": risk_name,
                            "matched_copy": fragment,
                            "source": line.strip(),
                            "context": context(lines, idx),
                        })

    OUT.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "count": len(results),
        "results": results,
    }

    (OUT / "copy-risk-lines.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = ["# FutureFunded Copy Risk Locator", ""]
    md.append(f"Generated: `{report['generated_at']}`")
    md.append(f"Findings: **{len(results)}**")
    md.append("")

    current = None
    for item in results:
        if item["file"] != current:
            current = item["file"]
            md.append(f"## `{current}`")
            md.append("")
        md.append(f"### Line {item['line']} — `{item['risk']}`")
        md.append("")
        md.append(f"Matched copy: `{item['matched_copy']}`")
        md.append("")
        md.append("```jinja")
        for row in item["context"]:
            marker = ">" if row["line"] == item["line"] else " "
            md.append(f"{marker} {row['line']}: {row['text']}")
        md.append("```")
        md.append("")

    if not results:
        md.append("No risky public copy found. ✅")
        md.append("")

    (OUT / "copy-risk-lines.md").write_text("\n".join(md), encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()

    shutil.copytree(OUT, LATEST)

    print(f"Copy risk locator complete: {len(results)} finding(s)")
    print(f"Report: {LATEST / 'copy-risk-lines.md'}")
    return 1 if results else 0

if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path.cwd()
CSS_DIRS = [
    ROOT / "apps/web/app/static/css",
    ROOT / "app/static/css",
]
TEMPLATE_DIRS = [
    ROOT / "apps/web/app/templates",
    ROOT / "app/templates",
    ROOT / "templates",
]

CSS_FILE_RE = re.compile(r"""css/([A-Za-z0-9_.-]+\.css)""")
URL_FOR_RE = re.compile(
    r"""url_for\(\s*['"]static['"]\s*,\s*filename\s*=\s*['"]css/([^'"]+\.css)['"]"""
)


class CssHrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        data = dict(attrs)
        href = data.get("href") or ""
        rel = (data.get("rel") or "").lower()
        if ".css" in href or rel == "stylesheet":
            self.hrefs.append(href)


def find_css_dir() -> Path:
    for d in CSS_DIRS:
        if d.exists():
            return d
    raise SystemExit("Could not find static css directory.")


def existing_css_files(css_dir: Path) -> set[str]:
    return {
        p.name
        for p in css_dir.iterdir()
        if p.is_file() and p.suffix == ".css" and ".bak" not in p.name
    }


def scan_static_refs() -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for base in TEMPLATE_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in {".html", ".jinja", ".j2", ".txt"}:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            found = set(URL_FOR_RE.findall(text))
            found.update(CSS_FILE_RE.findall(text))

            if found:
                refs[str(p.relative_to(ROOT))] = found
    return refs


def fetch_css_from_url(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "FutureFunded-CSS-Audit/1.0"})
    with urllib.request.urlopen(req, timeout=20) as res:
        html = res.read().decode("utf-8", errors="replace")

    parser = CssHrefParser()
    parser.feed(html)

    names: list[str] = []
    for href in parser.hrefs:
        absolute = urljoin(url, href)
        path = urlparse(absolute).path
        if "/static/css/" in path or path.endswith(".css"):
            names.append(Path(path).name)

    return names


def print_section(title: str) -> None:
    print()
    print("=" * len(title))
    print(title)
    print("=" * len(title))


def main() -> int:
    css_dir = find_css_dir()
    existing = existing_css_files(css_dir)
    static_refs = scan_static_refs()

    urls = sys.argv[1:] or [
        "http://127.0.0.1:5000/platform/",
        "http://127.0.0.1:5000/c/connect-atx-elite",
    ]

    print_section("CSS folder")
    print(css_dir.relative_to(ROOT))
    for name in sorted(existing):
        print(f"  {name}")

    print_section("Static template references")
    static_used: set[str] = set()
    for file, names in sorted(static_refs.items()):
        print(f"{file}")
        for name in sorted(names):
            static_used.add(name)
            marker = "OK" if name in existing else "MISSING"
            print(f"  [{marker}] {name}")

    print_section("Runtime rendered page CSS")
    runtime_used: set[str] = set()
    for url in urls:
        print(url)
        try:
            names = fetch_css_from_url(url)
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            continue

        if not names:
            print("  [WARN] no CSS hrefs found")

        for name in names:
            runtime_used.add(name)
            marker = "OK" if name in existing else "MISSING"
            print(f"  [{marker}] {name}")

    print_section("Likely active CSS")
    for name in sorted(static_used | runtime_used):
        marker = []
        if name in runtime_used:
            marker.append("runtime")
        if name in static_used:
            marker.append("template")
        print(f"  {name}  ({', '.join(marker)})")

    print_section("CSS files in folder not observed in platform/campaign runtime")
    unused = existing - runtime_used
    for name in sorted(unused):
        print(f"  {name}")

    print()
    if any(name not in existing for name in static_used | runtime_used):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

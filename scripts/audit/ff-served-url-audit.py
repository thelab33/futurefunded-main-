#!/usr/bin/env python3
"""
FutureFunded served URL + asset audit

Audits:
- Flask url_map GET routes when importable
- Known FutureFunded public/platform URLs
- Rendered HTML asset references
- CSS url(...) references
- Internal page links discovered from rendered pages
- Static files on disk vs live served assets
- Missing/broken served URLs

Output:
audit_outputs/served-url-audit-<timestamp>/
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import time
from collections import deque
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("FF_AUDIT_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
MAX_PAGES = int(os.environ.get("FF_AUDIT_MAX_PAGES", "160"))
TIMEOUT = float(os.environ.get("FF_AUDIT_TIMEOUT", "10"))
STAMP = time.strftime("%Y%m%d%H%M%S")
ROOT = Path.cwd()
OUT = ROOT / "audit_outputs" / f"served-url-audit-{STAMP}"
HTML_DIR = OUT / "rendered_pages"
STATIC_ROOT = ROOT / "apps/web/app/static"

IGNORE_SCHEMES = ("mailto:", "tel:", "sms:", "javascript:", "data:", "blob:", "about:")
ASSET_EXTS = {
    ".css", ".js", ".mjs", ".map",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".avif",
    ".woff", ".woff2", ".ttf", ".otf",
    ".json", ".webmanifest", ".xml", ".txt",
    ".mp4", ".webm", ".mov", ".mp3", ".wav",
    ".pdf",
}

CSS_URL_RE = re.compile(r"url\((?!['\"]?data:)(['\"]?)(.*?)\1\)", re.I)
FETCH_RE = re.compile(r"""(?:fetch|axios\.(?:get|post|put|delete))\(\s*['"]([^'"]+)['"]""")
SRCSET_SPLIT_RE = re.compile(r"\s*,\s*")


@dataclass
class FetchResult:
    url: str
    status: int | None
    content_type: str
    bytes: int
    final_url: str
    error: str = ""


@dataclass
class DiscoveredURL:
    url: str
    kind: str
    source: str
    attr: str = ""


class AssetParser(HTMLParser):
    def __init__(self, page_url: str):
        super().__init__()
        self.page_url = page_url
        self.assets: list[DiscoveredURL] = []
        self.links: list[DiscoveredURL] = []

    def add_url(self, value: str | None, kind: str, attr: str):
        if not value:
            return
        value = value.strip()
        if not value or value.startswith("#") or value.lower().startswith(IGNORE_SCHEMES):
            return

        # srcset: "image.webp 1x, image@2x.webp 2x"
        if attr == "srcset":
            for item in SRCSET_SPLIT_RE.split(value):
                first = item.strip().split(" ")[0] if item.strip() else ""
                self.add_url(first, kind, "srcset-item")
            return

        absolute = normalize_url(urljoin(self.page_url, value))
        if not absolute:
            return

        item = DiscoveredURL(url=absolute, kind=kind, source=self.page_url, attr=attr)
        if kind == "page-link":
            self.links.append(item)
        else:
            self.assets.append(item)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        a = {k.lower(): v for k, v in attrs}
        tag = tag.lower()

        if tag == "link":
            rel = (a.get("rel") or "").lower()
            href = a.get("href")
            if href:
                kind = "stylesheet" if "stylesheet" in rel else "link-asset"
                if "manifest" in rel:
                    kind = "manifest"
                elif "icon" in rel:
                    kind = "icon"
                elif "preload" in rel or "modulepreload" in rel:
                    kind = "preload"
                self.add_url(href, kind, "href")

        elif tag == "script":
            self.add_url(a.get("src"), "script", "src")

        elif tag == "img":
            self.add_url(a.get("src"), "image", "src")
            self.add_url(a.get("srcset"), "image", "srcset")

        elif tag == "source":
            self.add_url(a.get("src"), "media-source", "src")
            self.add_url(a.get("srcset"), "media-source", "srcset")

        elif tag in {"video", "audio"}:
            self.add_url(a.get("src"), tag, "src")
            self.add_url(a.get("poster"), "poster", "poster")

        elif tag == "a":
            self.add_url(a.get("href"), "page-link", "href")

        elif tag == "meta":
            content = a.get("content")
            prop = (a.get("property") or a.get("name") or "").lower()
            if content and any(x in prop for x in ["image", "url"]):
                self.add_url(content, "meta-url", "content")


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url or url.lower().startswith(IGNORE_SCHEMES):
        return ""
    url, _frag = urldefrag(url)
    return url


def same_origin(url: str) -> bool:
    a = urlparse(BASE_URL)
    b = urlparse(url)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def is_probable_asset(url: str) -> bool:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    return suffix in ASSET_EXTS or path.startswith("/static/")


def is_probable_page(url: str) -> bool:
    if not same_origin(url):
        return False
    path = urlparse(url).path
    if path.startswith("/static/"):
        return False
    suffix = Path(path).suffix.lower()
    return suffix == "" or suffix not in ASSET_EXTS


def fetch(url: str) -> FetchResult:
    req = Request(url, headers={"User-Agent": "FutureFundedAudit/1.0"})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            return FetchResult(
                url=url,
                status=getattr(r, "status", None),
                content_type=r.headers.get("content-type", ""),
                bytes=len(body),
                final_url=r.geturl(),
            )
    except HTTPError as e:
        try:
            body = e.read()
            size = len(body)
        except Exception:
            size = 0
        return FetchResult(
            url=url,
            status=e.code,
            content_type=e.headers.get("content-type", "") if e.headers else "",
            bytes=size,
            final_url=url,
            error=str(e),
        )
    except URLError as e:
        return FetchResult(url=url, status=None, content_type="", bytes=0, final_url=url, error=str(e.reason))
    except Exception as e:
        return FetchResult(url=url, status=None, content_type="", bytes=0, final_url=url, error=repr(e))


def fetch_body(url: str) -> tuple[FetchResult, bytes]:
    req = Request(url, headers={"User-Agent": "FutureFundedAudit/1.0"})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            return FetchResult(
                url=url,
                status=getattr(r, "status", None),
                content_type=r.headers.get("content-type", ""),
                bytes=len(body),
                final_url=r.geturl(),
            ), body
    except HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return FetchResult(
            url=url,
            status=e.code,
            content_type=e.headers.get("content-type", "") if e.headers else "",
            bytes=len(body),
            final_url=url,
            error=str(e),
        ), body
    except Exception as e:
        return FetchResult(url=url, status=None, content_type="", bytes=0, final_url=url, error=repr(e)), b""


def route_urls_from_flask() -> list[str]:
    urls: list[str] = []
    errors: list[str] = []

    try:
        from apps.web.app import create_app  # type: ignore

        app = create_app()
        with app.app_context():
            for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
                methods = getattr(rule, "methods", set()) or set()
                if "GET" not in methods:
                    continue
                if "<" in rule.rule:
                    continue
                urls.append(urljoin(BASE_URL + "/", rule.rule.lstrip("/")))
    except Exception as e:
        errors.append(repr(e))

    (OUT / "flask_url_map_import_errors.txt").write_text("\n".join(errors) if errors else "none\n")
    return urls


def known_seed_urls() -> list[str]:
    return [
        f"{BASE_URL}/",
        f"{BASE_URL}/healthz",
        f"{BASE_URL}/platform/",
        f"{BASE_URL}/platform/onboarding",
        f"{BASE_URL}/platform/login",
        f"{BASE_URL}/platform/dashboard?access_token=dev-operator-20260529123018",
        f"{BASE_URL}/c/connect-atx-elite",
    ]


def write_csv(path: Path, rows: Iterable[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def safe_html_name(url: str) -> str:
    p = urlparse(url)
    raw = (p.path.strip("/") or "root") + (("__" + p.query) if p.query else "")
    raw = re.sub(r"[^a-zA-Z0-9_.=-]+", "_", raw)
    return raw[:160] + ".html"


def disk_static_files() -> list[dict]:
    rows = []
    if not STATIC_ROOT.exists():
        return rows

    for p in sorted(STATIC_ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(STATIC_ROOT).as_posix()
        try:
            data = p.read_bytes()
            sha = hashlib.sha256(data).hexdigest()[:16]
            size = len(data)
        except Exception:
            sha = ""
            size = p.stat().st_size
        rows.append({
            "disk_path": str(p),
            "static_url": f"/static/{rel}",
            "size": size,
            "sha256_16": sha,
            "ext": p.suffix.lower(),
        })
    return rows


def css_urls(css_url: str, css_text: str) -> list[DiscoveredURL]:
    found = []
    for _quote, raw in CSS_URL_RE.findall(css_text):
        raw = raw.strip()
        if not raw or raw.lower().startswith(IGNORE_SCHEMES):
            continue
        absolute = normalize_url(urljoin(css_url, raw))
        if absolute:
            found.append(DiscoveredURL(url=absolute, kind="css-url", source=css_url, attr="url()"))
    return found


def js_references(js_url: str, js_text: str) -> list[DiscoveredURL]:
    found = []
    for raw in FETCH_RE.findall(js_text):
        absolute = normalize_url(urljoin(js_url, raw))
        if absolute:
            found.append(DiscoveredURL(url=absolute, kind="js-fetch-ref", source=js_url, attr="fetch()"))
    return found


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    route_seed = []
    route_seed.extend(route_urls_from_flask())
    route_seed.extend(known_seed_urls())

    seen_pages: set[str] = set()
    seen_assets: dict[str, DiscoveredURL] = {}
    external_urls: dict[str, DiscoveredURL] = {}
    page_results: list[dict] = []
    asset_results: list[dict] = []

    q = deque(dict.fromkeys(normalize_url(u) for u in route_seed if normalize_url(u)))

    while q and len(seen_pages) < MAX_PAGES:
        page_url = q.popleft()
        if not page_url or page_url in seen_pages:
            continue
        if not same_origin(page_url):
            continue
        if is_probable_asset(page_url):
            seen_assets.setdefault(page_url, DiscoveredURL(page_url, "direct-asset", "route-seed"))
            continue

        seen_pages.add(page_url)
        result, body = fetch_body(page_url)
        page_results.append(asdict(result))

        ctype = result.content_type.lower()
        if result.status and 200 <= result.status < 300 and ("html" in ctype or body.strip().startswith(b"<!DOCTYPE") or b"<html" in body[:500].lower()):
            name = safe_html_name(page_url)
            (HTML_DIR / name).write_bytes(body)

            html = body.decode("utf-8", errors="replace")
            parser = AssetParser(page_url)
            parser.feed(html)

            for asset in parser.assets:
                if same_origin(asset.url):
                    seen_assets.setdefault(asset.url, asset)
                else:
                    external_urls.setdefault(asset.url, asset)

            for link in parser.links:
                if same_origin(link.url) and is_probable_page(link.url):
                    if link.url not in seen_pages and len(seen_pages) + len(q) < MAX_PAGES:
                        q.append(link.url)
                else:
                    external_urls.setdefault(link.url, link)

    # Fetch assets and discover nested CSS/JS refs.
    asset_queue = deque(seen_assets.values())
    fetched_assets: set[str] = set()

    while asset_queue:
        item = asset_queue.popleft()
        if item.url in fetched_assets:
            continue
        fetched_assets.add(item.url)

        result, body = fetch_body(item.url)
        row = asdict(result)
        row.update({"kind": item.kind, "source": item.source, "attr": item.attr})
        asset_results.append(row)

        text = ""
        ctype = (result.content_type or "").lower()
        path = urlparse(item.url).path.lower()

        if body and (("text/css" in ctype) or path.endswith(".css")):
            text = body.decode("utf-8", errors="replace")
            for nested in css_urls(item.url, text):
                if same_origin(nested.url) and nested.url not in seen_assets:
                    seen_assets[nested.url] = nested
                    asset_queue.append(nested)
                elif not same_origin(nested.url):
                    external_urls.setdefault(nested.url, nested)

        elif body and (("javascript" in ctype) or path.endswith((".js", ".mjs"))):
            text = body.decode("utf-8", errors="replace")
            for nested in js_references(item.url, text):
                if same_origin(nested.url):
                    if is_probable_asset(nested.url) and nested.url not in seen_assets:
                        seen_assets[nested.url] = nested
                        asset_queue.append(nested)
                else:
                    external_urls.setdefault(nested.url, nested)

    disk_rows = disk_static_files()
    served_static_paths = {
        urlparse(row["url"]).path for row in asset_results
        if urlparse(row["url"]).path.startswith("/static/")
    }

    unserved_disk = [
        row for row in disk_rows
        if row["static_url"] not in served_static_paths
    ]

    missing_rows = []
    for row in page_results:
        status = row.get("status")
        if status is None or int(status) >= 400:
            missing_rows.append({"type": "page", **row})
    for row in asset_results:
        status = row.get("status")
        if status is None or int(status) >= 400:
            missing_rows.append({"type": "asset", **row})

    external_rows = [asdict(v) for v in external_urls.values()]

    write_csv(OUT / "pages.csv", page_results, ["url", "status", "content_type", "bytes", "final_url", "error"])
    write_csv(OUT / "assets.csv", asset_results, ["url", "kind", "source", "attr", "status", "content_type", "bytes", "final_url", "error"])
    write_csv(OUT / "missing_or_broken.csv", missing_rows, ["type", "url", "kind", "source", "attr", "status", "content_type", "bytes", "final_url", "error"])
    write_csv(OUT / "external_urls.csv", external_rows, ["url", "kind", "source", "attr"])
    write_csv(OUT / "static_files_on_disk.csv", disk_rows, ["disk_path", "static_url", "size", "sha256_16", "ext"])
    write_csv(OUT / "static_files_not_seen_live.csv", unserved_disk, ["disk_path", "static_url", "size", "sha256_16", "ext"])

    summary = {
        "base_url": BASE_URL,
        "timestamp": STAMP,
        "pages_checked": len(page_results),
        "assets_checked": len(asset_results),
        "external_urls_found": len(external_rows),
        "missing_or_broken": len(missing_rows),
        "static_files_on_disk": len(disk_rows),
        "static_files_not_seen_live": len(unserved_disk),
        "output_dir": str(OUT),
    }

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    missing_preview = "\n".join(
        f"- [{r.get('status')}] {r.get('type')} {r.get('url')} from {r.get('source', '')}"
        for r in missing_rows[:60]
    ) or "- none"

    report = f"""# FutureFunded Served URL Audit

Generated: `{STAMP}`  
Base URL: `{BASE_URL}`

## Summary

| Check | Count |
|---|---:|
| Pages checked | {len(page_results)} |
| Assets checked | {len(asset_results)} |
| External URLs found | {len(external_rows)} |
| Missing/broken URLs | {len(missing_rows)} |
| Static files on disk | {len(disk_rows)} |
| Static files not seen in live pages | {len(unserved_disk)} |

## Missing / Broken Preview

{missing_preview}

## Files Created

- `pages.csv`
- `assets.csv`
- `missing_or_broken.csv`
- `external_urls.csv`
- `static_files_on_disk.csv`
- `static_files_not_seen_live.csv`
- `rendered_pages/`
- `summary.json`

## Next Commands

```bash
sed -n '1,220p' "{OUT}/served-url-audit.md"
column -s, -t "{OUT}/missing_or_broken.csv" | sed -n '1,120p'
column -s, -t "{OUT}/assets.csv" | sed -n '1,160p'

"""
(OUT / "served-url-audit.md").write_text(report, encoding="utf-8")

print(json.dumps(summary, indent=2))
print()
print(f"✅ Report: {OUT}/served-url-audit.md")
print(f"✅ Missing: {OUT}/missing_or_broken.csv")
print(f"✅ Assets:  {OUT}/assets.csv")
return 0

if __name__ == "__main__":
    raise SystemExit(main())

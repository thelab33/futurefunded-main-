#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


STATIC_EXTENSIONS = {
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".map", ".pdf", ".zip", ".mp4", ".webm",
}

DEFAULT_SEEDS = [
    ("/platform/", "Platform homepage"),
    ("/c/connect-atx-elite", "Campaign page"),
    ("/platform/login", "Operator login"),
    ("/platform/onboarding", "Launch onboarding"),
    ("/platform/dashboard", "Dashboard locked"),
]


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.assets: list[str] = []
        self.forms: list[dict] = []
        self.buttons = 0
        self.anchors = 0
        self.img_missing_alt = 0
        self.inputs_without_labelish = 0
        self.main_count = 0
        self.h1_count = 0
        self.skip_link = False
        self.html_attrs: dict[str, str] = {}
        self.body_attrs: dict[str, str] = {}
        self._current_form: dict | None = None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {k: (v or "") for k, v in attrs_list}

        if tag == "html":
            self.html_attrs.update(attrs)
        elif tag == "body":
            self.body_attrs.update(attrs)

        if tag == "main":
            self.main_count += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "button":
            self.buttons += 1
        elif tag == "a":
            self.anchors += 1
            href = attrs.get("href", "").strip()
            if href:
                self.links.append(href)
            if href.startswith("#") and ("skip" in attrs.get("class", "").lower() or "skip" in attrs.get("aria-label", "").lower()):
                self.skip_link = True
        elif tag in {"link", "script", "img", "source"}:
            asset = attrs.get("href") or attrs.get("src") or ""
            if asset:
                self.assets.append(asset)
            if tag == "img" and "alt" not in attrs:
                self.img_missing_alt += 1
        elif tag == "form":
            self._current_form = {
                "action": attrs.get("action", ""),
                "method": attrs.get("method", "get").lower(),
                "inputs": 0,
                "has_csrf": False,
            }
            self.forms.append(self._current_form)
        elif tag == "input":
            if self._current_form is not None:
                self._current_form["inputs"] += 1
                if attrs.get("name") in {"csrf_token", "csrf"}:
                    self._current_form["has_csrf"] = True

            input_type = attrs.get("type", "text").lower()
            if input_type not in {"hidden", "submit", "button", "checkbox", "radio"}:
                if not attrs.get("id") and not attrs.get("aria-label") and not attrs.get("aria-labelledby"):
                    self.inputs_without_labelish += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._current_form = None


@dataclass
class SurfaceResult:
    label: str
    url: str
    redacted_url: str
    status: int | str
    content_type: str
    final_url: str
    title: str
    ui_markers: list[str]
    body_classes: str
    h1_count: int
    main_count: int
    anchors: int
    buttons: int
    forms: int
    img_missing_alt: int
    inputs_without_labelish: int
    css_assets: list[str]
    js_assets: list[str]
    linked_pages: list[str]
    flags: list[str]
    priority: str


def redact_url(url: str) -> str:
    p = urlparse(url)
    q = []
    for k, v in parse_qsl(p.query, keep_blank_values=True):
        if k.lower() in {"token", "operator_token", "access_token", "secret", "key"}:
            q.append((k, "REDACTED"))
        else:
            q.append((k, v))
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))


def normalize_url(url: str) -> str:
    p = urlparse(url)
    q = []
    for k, v in parse_qsl(p.query, keep_blank_values=True):
        # keep cache-busters and non-secret query params; secrets are kept internally but redacted in reports
        q.append((k, v))
    clean = urlunparse((p.scheme, p.netloc, p.path or "/", "", urlencode(q), ""))
    return clean


def is_same_origin_page(base: str, href: str) -> bool:
    if not href:
        return False
    href = href.strip()
    if href.startswith(("#", "mailto:", "tel:", "sms:", "javascript:", "data:")):
        return False

    absolute = urljoin(base, href)
    base_p = urlparse(base)
    p = urlparse(absolute)

    if p.netloc != base_p.netloc or p.scheme != base_p.scheme:
        return False

    lower_path = p.path.lower()
    if lower_path.startswith(("/static/", "/assets/", "/cdn-cgi/")):
        return False

    if any(lower_path.endswith(ext) for ext in STATIC_EXTENSIONS):
        return False

    # Keep page-like app routes, skip obvious API/webhook endpoints for this visual closeout map.
    if lower_path.startswith(("/api/", "/c/stripe/webhook")):
        return False

    return True


def fetch(url: str, timeout: int = 12) -> tuple[int | str, str, str, str]:
    req = Request(
        url,
        headers={
            "User-Agent": "FutureFundedCloseoutAuditor/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as res:
            raw = res.read()
            ctype = res.headers.get("content-type", "")
            charset = "utf-8"
            match = re.search(r"charset=([^;\s]+)", ctype, flags=re.I)
            if match:
                charset = match.group(1)
            return res.status, ctype, res.geturl(), raw.decode(charset, errors="ignore")
    except HTTPError as exc:
        raw = exc.read()
        ctype = exc.headers.get("content-type", "") if exc.headers else ""
        return exc.code, ctype, exc.geturl(), raw.decode("utf-8", errors="ignore")
    except URLError as exc:
        return f"ERR:{type(exc).__name__}", "", url, str(exc)
    except Exception as exc:
        return f"ERR:{type(exc).__name__}", "", url, str(exc)


def extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def extract_markers(html: str) -> list[str]:
    markers = []
    patterns = [
        r'data-ff-(?:page|template|ui-version|surface|system-loop|dashboard-layout|dashboard-main-layout)=["\']([^"\']+)["\']',
        r'class=["\']([^"\']*(?:ff-[^"\']+)[^"\']*)["\']',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, html, flags=re.I):
            value = re.sub(r"\s+", " ", m.group(1)).strip()
            if value and value not in markers:
                markers.append(value)
            if len(markers) >= 12:
                break
    return markers[:12]


def classify_flags(url: str, status: int | str, html: str, parser: SurfaceParser, title: str) -> tuple[list[str], str]:
    flags: list[str] = []
    priority = "P2"

    path = urlparse(url).path
    htmlish = "html" in html[:500].lower() or "<html" in html.lower()

    expected_locked_dashboard = path.rstrip("/") == "/platform/dashboard" and not any(
        key in urlparse(url).query for key in ["operator_token=", "token="]
    )

    if isinstance(status, str):
        flags.append(f"fetch-error:{status}")
        return flags, "P0"

    if status >= 500:
        flags.append(f"server-error:{status}")
        priority = "P0"
    elif status == 404:
        flags.append("not-found")
        priority = "P0"
    elif status == 403 and expected_locked_dashboard:
        flags.append("expected-locked-dashboard")
        priority = "OK"
    elif status >= 400:
        flags.append(f"http-{status}")
        priority = "P1"

    if htmlish and status < 500:
        if not title:
            flags.append("missing-title")
            priority = min_priority(priority, "P1")
        if parser.h1_count == 0:
            flags.append("missing-h1")
            priority = min_priority(priority, "P1")
        if parser.main_count == 0:
            flags.append("missing-main")
            priority = min_priority(priority, "P1")
        if parser.img_missing_alt:
            flags.append(f"images-missing-alt:{parser.img_missing_alt}")
            priority = min_priority(priority, "P1")
        if parser.inputs_without_labelish:
            flags.append(f"inputs-need-label-review:{parser.inputs_without_labelish}")
            priority = min_priority(priority, "P1")

        css_blob = "\n".join(parser.assets)
        if "/static/css/ff.css" not in css_blob and "ff.css" not in css_blob:
            flags.append("missing-ff-css")
            priority = min_priority(priority, "P1")

        if "ff.checkout.css" in css_blob:
            flags.append("legacy-checkout-css-present-review-later")
        if "ff-embedded-checkout.js" in "\n".join(parser.assets):
            flags.append("legacy-embedded-checkout-js-present-review-later")

        if "operator_token=" in html or "token=" in html:
            if "data-ff-dashboard-root" in html:
                flags.append("authenticated-page-contains-tokenized-next-values-review-later")

    if not flags:
        flags.append("clean")

    if priority == "P2" and flags == ["clean"]:
        priority = "OK"

    return flags, priority


def min_priority(current: str, candidate: str) -> str:
    order = {"P0": 0, "P1": 1, "P2": 2, "OK": 3}
    return candidate if order.get(candidate, 9) < order.get(current, 9) else current


def audit_surface(label: str, url: str, asset_v: str = "") -> tuple[SurfaceResult, list[str]]:
    if asset_v and "css_v=" not in url and "v=" not in url:
        sep = "&" if urlparse(url).query else "?"
        url = f"{url}{sep}css_v={asset_v}"

    status, ctype, final_url, html = fetch(url)

    parser = SurfaceParser()
    if html:
        try:
            parser.feed(html)
        except Exception:
            pass

    base_for_links = final_url if isinstance(status, int) else url
    linked_pages = []
    for href in parser.links:
        if is_same_origin_page(base_for_links, href):
            linked_pages.append(normalize_url(urljoin(base_for_links, href)))

    linked_pages = sorted(set(linked_pages))
    css_assets = sorted({a for a in parser.assets if ".css" in a})
    js_assets = sorted({a for a in parser.assets if ".js" in a})

    title = extract_title(html)
    markers = extract_markers(html)
    body_classes = parser.body_attrs.get("class", "")

    flags, priority = classify_flags(url, status, html, parser, title)

    return SurfaceResult(
        label=label,
        url=url,
        redacted_url=redact_url(url),
        status=status,
        content_type=ctype,
        final_url=redact_url(final_url),
        title=title,
        ui_markers=markers,
        body_classes=body_classes,
        h1_count=parser.h1_count,
        main_count=parser.main_count,
        anchors=parser.anchors,
        buttons=parser.buttons,
        forms=len(parser.forms),
        img_missing_alt=parser.img_missing_alt,
        inputs_without_labelish=parser.inputs_without_labelish,
        css_assets=css_assets,
        js_assets=js_assets,
        linked_pages=[redact_url(x) for x in linked_pages],
        flags=flags,
        priority=priority,
    ), linked_pages


def build_markdown(results: list[SurfaceResult], label: str, base: str) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    grouped = {"P0": [], "P1": [], "P2": [], "OK": []}
    for r in results:
        grouped.setdefault(r.priority, []).append(r)

    lines = [
        f"# FutureFunded launch closeout surface map — {label}",
        "",
        f"- Generated: `{now}`",
        f"- Base: `{base}`",
        f"- Surfaces checked: `{len(results)}`",
        "",
        "## Executive launch call",
        "",
    ]

    if grouped["P0"]:
        lines.append("**P0 blockers exist. Do not hand off until these are fixed.**")
    elif grouped["P1"]:
        lines.append("**No P0 blockers found. P1 polish remains; choose only launch-critical items.**")
    else:
        lines.append("**No P0/P1 issues found by static crawl. Visual/payment smoke still required.**")

    lines += [
        "",
        "## Surface table",
        "",
        "| Priority | Status | Surface | Title | Flags |",
        "|---|---:|---|---|---|",
    ]

    for r in sorted(results, key=lambda x: ({"P0":0, "P1":1, "P2":2, "OK":3}.get(x.priority, 9), x.label)):
        flags = ", ".join(r.flags[:5])
        lines.append(
            f"| {r.priority} | {r.status} | `{r.redacted_url}` | {safe_cell(r.title or r.label)} | {safe_cell(flags)} |"
        )

    lines += [
        "",
        "## Today-only closeout roadmap",
        "",
        "### P0 — must fix before sister/demo handoff",
    ]

    if grouped["P0"]:
        for r in grouped["P0"]:
            lines.append(f"- `{r.redacted_url}` — {', '.join(r.flags)}")
    else:
        lines.append("- No P0 route/status blockers found by this crawl.")

    lines += [
        "",
        "### P1 — polish only if it affects trust or money flow",
    ]

    if grouped["P1"]:
        for r in grouped["P1"][:12]:
            lines.append(f"- `{r.redacted_url}` — {', '.join(r.flags)}")
    else:
        lines.append("- No P1 structural/accessibility flags found by this crawl.")

    lines += [
        "",
        "### P2 — do not chase today unless visually obvious",
        "- Legacy checkout CSS/JS references can be consolidated later if payment smoke remains green.",
        "- Static demo values on dashboard should eventually wire to ledger data, but do not block today if checkout and ledger work.",
        "- Cosmetic micro-polish should stop once visual board + money loop pass.",
        "",
        "## Recommended final command sequence",
        "",
        "```bash",
        "node scripts/audit/ff_visual_surface_board.mjs",
        "bash scripts/release/verify-stripe-network.sh",
        "git status --short",
        "```",
        "",
    ]

    return "\n".join(lines) + "\n"


def safe_cell(value: str) -> str:
    return re.sub(r"[\n\r|]+", " ", value).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:5000", help="Base URL to crawl")
    parser.add_argument("--label", default="local", help="Report label")
    parser.add_argument("--asset-v", default=os.environ.get("FF_ASSET_V", "closeout-map"), help="Cache-busting css_v")
    parser.add_argument("--max-pages", type=int, default=80)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--include-auth-dashboard", action="store_true")
    parser.add_argument("--token-file", default="/tmp/ff_operator_token")
    parser.add_argument("--output-dir", default="audit_outputs/launch-closeout/latest")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    seeds: list[tuple[str, str]] = [(urljoin(base + "/", p.lstrip("/")), label) for p, label in DEFAULT_SEEDS]

    token = ""
    token_path = Path(args.token_file)
    if args.include_auth_dashboard and token_path.exists():
        token = token_path.read_text(encoding="utf-8", errors="ignore").strip()

    if args.include_auth_dashboard and token:
        seeds.append((f"{base}/platform/dashboard?operator_token={token}", "Dashboard authenticated"))
    elif args.include_auth_dashboard:
        print("WARN: --include-auth-dashboard set, but no token file found.", file=sys.stderr)

    seen: set[str] = set()
    q = deque((url, label, 0) for url, label in seeds)
    results: list[SurfaceResult] = []

    while q and len(results) < args.max_pages:
        url, label, depth = q.popleft()
        key = normalize_url(url)

        # Never let tokenized URLs explode the crawl.
        redacted_key = redact_url(key)
        if redacted_key in seen:
            continue
        seen.add(redacted_key)

        result, links = audit_surface(label, url, args.asset_v)
        results.append(result)

        if depth < args.max_depth:
            for link in links:
                if len(results) + len(q) >= args.max_pages:
                    break
                if redact_url(normalize_url(link)) not in seen:
                    q.append((link, "Linked page", depth + 1))

        time.sleep(0.04)

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    data = {
        "label": args.label,
        "base": base,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results": [asdict(r) for r in results],
    }

    (outdir / "surface-map.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    md = build_markdown(results, args.label, base)
    (outdir / "surface-roadmap.md").write_text(md, encoding="utf-8")

    docs_dir = Path("docs/launch-closeout")
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "sister-today-roadmap.md").write_text(md, encoding="utf-8")

    p0 = sum(1 for r in results if r.priority == "P0")
    p1 = sum(1 for r in results if r.priority == "P1")

    print()
    print("FutureFunded closeout surface map")
    print("=" * 42)
    print(f"Base:       {base}")
    print(f"Label:      {args.label}")
    print(f"Checked:    {len(results)} surfaces")
    print(f"P0:         {p0}")
    print(f"P1:         {p1}")
    print(f"JSON:       {outdir / 'surface-map.json'}")
    print(f"Roadmap:    {outdir / 'surface-roadmap.md'}")
    print(f"Doc copy:   {docs_dir / 'sister-today-roadmap.md'}")
    print()

    for r in results:
        if r.priority in {"P0", "P1"}:
            print(f"{r.priority} {r.status} {r.redacted_url}")
            print(f"  flags: {', '.join(r.flags)}")

    return 1 if p0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

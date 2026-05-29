#!/usr/bin/env python3
"""
FutureFunded • Wave 0 + Wave 1 Launch Contract Audit v2

Read-only launch audit:
- Excludes backups/tmp/quarantine folders by default.
- Separates source-template checks from rendered-page checks.
- Does not falsely treat raw Jinja source syntax as public rendered leaks.
- Applies full CTA contract checks only to rendered pages and full-page templates.
- Produces Markdown + JSON reports in ./audit_outputs.

Usage:
  python scripts/audit/ff_launch_contract_audit.py \
    --base-url http://127.0.0.1:5000 \
    --live-url https://getfuturefunded.com/platform/ \
    --live-url https://getfuturefunded.com/c/connect-atx-elite

Optional:
  --include-backups
  --skip-network
  --strict
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


AUDIT_VERSION = "wave0-wave1-v2"

TEXT_EXTS = {
    ".py", ".html", ".jinja", ".j2", ".css", ".js", ".ts", ".tsx", ".svelte",
    ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".env", ".example",
}

BASE_SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", ".svelte-kit", ".next",
    "playwright-report", "test-results", "audit_outputs", "htmlcov",
}

BACKUP_SKIP_HINTS = {
    ".ff-backups",
    ".template-backups",
    "tmp",
    "backups",
    "backup",
    "deprecated-backups",
    "quarantine",
    "stripe-embedded-backups",
}

CANONICAL_ROOTS = (
    "apps/web/app",
    "apps/api",
    "scripts",
    "tests",
)

RENDER_URLS_DEFAULT = [
    "/platform",
    "/platform/onboarding",
    "/platform/dashboard",
    "/c/connect-atx-elite",
]

EXPECTED_ROUTES = {
    "platform_home": ["/platform"],
    "platform_onboarding": ["/platform/onboarding"],
    "platform_dashboard": ["/platform/dashboard", "/dashboard"],
    "campaign_public": ["/c/<slug>", "/c/connect-atx-elite"],
    "campaign_checkout": ["/checkout/session", "/checkout/embedded-session", "/session-status"],
    "stripe_webhook": ["/stripe/webhook", "/webhooks/stripe"],
    "sponsor": ["/sponsor", "/sponsors", "/lead"],
}

# Source-safe leak patterns: these should not appear even in source accidentally.
SOURCE_LEAK_PATTERNS = [
    (r"<built-in method\b", "Python built-in method repr appears in source."),
    (r"\bbound method\b", "Python bound method repr appears in source."),
    (r"\bobject at 0x[0-9a-fA-F]+\b", "Python object repr appears in source."),
    (r"\bTraceback \(most recent call last\)", "Traceback appears in source."),
]

# Rendered-only leak patterns.
RENDERED_LEAK_PATTERNS = [
    (r"<built-in method\b", "Rendered Python method leaked into public HTML."),
    (r"\bbound method\b", "Rendered Python bound method leaked into public HTML."),
    (r"\bobject at 0x[0-9a-fA-F]+\b", "Python object repr leaked into public HTML."),
    (r"\bUndefinedError\b", "Jinja UndefinedError leaked into public HTML."),
    (r"\bjinja2\.exceptions\b", "Jinja exception leaked into public HTML."),
    (r"\bTraceback \(most recent call last\)", "Python traceback leaked into public HTML."),
    (r"\bNoneType\b", "Python NoneType leaked into public HTML."),
    (r"\{\{\s*[^}]+\s*\}\}", "Unrendered Jinja variable appears in rendered HTML."),
    (r"\{%\s*[^%]+\s*%\}", "Unrendered Jinja block appears in rendered HTML."),
]

STALE_PATTERNS = [
    (r"\bTODO\b", "TODO marker still present."),
    (r"\bFIXME\b", "FIXME marker still present."),
    (r"\bHACK\b", "HACK marker still present."),
    (r"\bplaceholder\b", "Placeholder language still present."),
    (r"\blorem ipsum\b", "Lorem ipsum placeholder content."),
    (r"\bdummy\b", "Dummy/test content language."),
    (r"\bfake\b", "Fake content language."),
    (r"\bstub\b", "Stub implementation language."),
    (r"\bnot wired\b", "Not-wired implementation language."),
    (r"\bcoming soon\b", "Coming-soon language may indicate incomplete product surface."),
    (r"\btest only\b", "Test-only language present."),
    (r"\brescue\b", "Rescue patch/version marker present."),
    (r"\bemergency\b", "Emergency patch/version marker present."),
]

ROUTE_DECORATOR_RE = re.compile(
    r"""@\s*(?:\w+\.)?(?:route|get|post|put|delete|patch)\(\s*["'](?P<route>[^"']+)["']""",
    re.I,
)

ASSET_VERSION_RE = re.compile(
    r"""(?P<asset>/static/[^"'\s>)]+?\.(?:css|js))\?v=(?P<version>[^"'\s>)]+)""",
    re.I,
)

SELECTOR_RE = re.compile(
    r"""(?:querySelector|querySelectorAll)\(\s*["'](?P<selector>[^"']+)["']\s*\)|getElementById\(\s*["'](?P<id>[^"']+)["']\s*\)""",
    re.I,
)

EMAIL_HINT_RE = re.compile(
    r"\b(email|mail|smtp|sendgrid|postmark|ses|outbox|receipt|thank.?you|confirmation|donor.?receipt|sponsor.?confirmation)\b",
    re.I,
)

PAYMENT_HINT_RE = re.compile(
    r"\b(stripe|paypal|checkout|webhook|payment_intent|checkout\.Session|payment_status|session-status)\b",
    re.I,
)

SPONSOR_HINT_RE = re.compile(
    r"\b(sponsor|partner|tier|recognition|logo|business|lead)\b",
    re.I,
)

OPERATOR_HINT_RE = re.compile(
    r"\b(operator|dashboard|onboarding|admin|ledger|export|csv|setup)\b",
    re.I,
)


@dataclass
class Issue:
    severity: str
    wave: str
    area: str
    location: str
    line: Optional[int]
    message: str
    recommendation: str


@dataclass
class Element:
    tag: str
    text: str
    attrs: Dict[str, str]
    source: str
    line: Optional[int] = None

    @property
    def href(self) -> str:
        return self.attrs.get("href", "")

    @property
    def cls(self) -> str:
        return self.attrs.get("class", "")


class PageParser(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.elements: List[Element] = []
        self.ids: List[str] = []
        self._stack: List[Tuple[str, Dict[str, str], int, List[str]]] = []

    def handle_starttag(self, tag: str, attrs_list):
        attrs = {k.lower(): (v or "") for k, v in attrs_list}
        line, _ = self.getpos()
        tag = tag.lower()

        if attrs.get("id"):
            self.ids.append(attrs["id"])

        if tag in {"a", "button", "form", "input", "summary", "select", "textarea"}:
            self._stack.append((tag, attrs, line, []))

        if tag == "input":
            label = attrs.get("aria-label") or attrs.get("value") or attrs.get("name") or attrs.get("id") or ""
            self.elements.append(Element("input", clean_text(label), attrs, self.source, line))

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        for i in range(len(self._stack) - 1, -1, -1):
            start_tag, attrs, line, chunks = self._stack[i]
            if start_tag == tag:
                text = clean_text(" ".join(chunks))
                self.elements.append(Element(start_tag, text, attrs, self.source, line))
                del self._stack[i]
                break

    def handle_data(self, data: str):
        if not data:
            return
        for i, item in enumerate(self._stack):
            tag, attrs, line, chunks = item
            chunks.append(data)
            self._stack[i] = (tag, attrs, line, chunks)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTS or path.name in {
        ".env", ".flaskenv", "Procfile", "Dockerfile", "Makefile"
    }


def is_backupish(path: Path) -> bool:
    parts = set(path.parts)
    lowered = str(path).lower()
    if parts & BACKUP_SKIP_HINTS:
        return True
    return any(hint in lowered for hint in BACKUP_SKIP_HINTS)


def should_skip(path: Path, include_backups: bool) -> bool:
    if any(part in BASE_SKIP_DIRS for part in path.parts):
        return True
    if not include_backups and is_backupish(path):
        return True
    return False


def is_canonical(path: Path, root: Path) -> bool:
    rp = rel(root, path)
    return rp.startswith(CANONICAL_ROOTS)


def collect_files(root: Path, include_backups: bool) -> List[Path]:
    files = []
    for p in root.rglob("*"):
        if should_skip(p, include_backups):
            continue
        if not p.is_file() or not is_text_file(p):
            continue
        if not is_canonical(p, root):
            continue
        try:
            if p.stat().st_size > 4_000_000:
                continue
        except Exception:
            continue
        files.append(p)
    return sorted(files)


def add_issue(issues, severity, wave, area, location, line, message, recommendation):
    issues.append(Issue(severity, wave, area, location, line, message, recommendation))


def severity_rank(sev: str) -> int:
    return {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(sev, 99)


def issue_sort_key(issue: Issue):
    return (severity_rank(issue.severity), issue.wave, issue.area, issue.location, issue.line or 0)


def fetch_url(url: str, timeout: int = 12):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"FutureFundedLaunchAudit/{AUDIT_VERSION}",
            "Accept": "text/html,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace"), getattr(resp, "status", None), None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return body, exc.code, str(exc)
    except Exception as exc:
        return None, None, str(exc)


def normalize_url(base_url: str, path_or_url: str) -> str:
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path_or_url.lstrip("/"))


def parse_page(source_name: str, content: str):
    parser = PageParser(source_name)
    try:
        parser.feed(content)
    except Exception:
        pass

    elements = parser.elements
    return {
        "source": source_name,
        "ids": parser.ids,
        "elements": elements,
        "anchors": [e for e in elements if e.tag == "a"],
        "buttons": [e for e in elements if e.tag == "button"],
        "forms": [e for e in elements if e.tag == "form"],
        "inputs": [e for e in elements if e.tag == "input"],
    }


def page_kind(source: str, full_page: bool) -> str:
    s = source.lower()
    if not full_page:
        return "partial"
    if "/login" in s or "platform/login" in s:
        return "auth"
    if "/dashboard" in s or "platform/dashboard" in s:
        return "operator"
    if "/c/" in s or "campaign" in s or "campaign_premium" in s:
        return "campaign"
    if "/platform" in s or "platform/" in s:
        return "platform"
    return "generic"


def is_full_page_template(path: Path, root: Path) -> bool:
    rp = rel(root, path).replace("\\", "/")
    name = path.name
    if name.startswith("_"):
        return False
    return (
        rp.endswith("templates/campaign_premium.html")
        or rp.endswith("templates/campaign/index.html")
        or rp.endswith("templates/platform/index.html")
        or rp.endswith("templates/platform/onboarding.html")
        or rp.endswith("templates/platform/dashboard.html")
    )


def element_summary(e: Element) -> Dict[str, Any]:
    return {
        "tag": e.tag,
        "text": clean_text(e.text)[:140],
        "href": e.attrs.get("href", ""),
        "id": e.attrs.get("id", ""),
        "class": e.attrs.get("class", "")[:180],
        "type": e.attrs.get("type", ""),
        "action": e.attrs.get("action", ""),
        "method": e.attrs.get("method", ""),
        "data_attrs": {k: v for k, v in e.attrs.items() if k.startswith("data-")},
        "line": e.line,
    }


def scan_page_contract(page, content: str, issues: List[Issue], *, rendered: bool, full_page: bool):
    source = page["source"]
    anchors = page["anchors"]
    buttons = page["buttons"]
    forms = page["forms"]
    ids = page["ids"]
    kind = page_kind(source, full_page)

    id_counts = Counter(ids)
    duplicate_ids = {k: v for k, v in id_counts.items() if v > 1}
    for id_value, count in duplicate_ids.items():
        add_issue(
            issues, "HIGH", "Wave 1", "HTML integrity", source, None,
            f"Duplicate id detected: #{id_value} appears {count} times.",
            "IDs must be unique. Duplicate IDs break anchors, JS selectors, forms, and accessibility.",
        )

    if rendered:
        for pattern, msg in RENDERED_LEAK_PATTERNS:
            for m in re.finditer(pattern, content, re.I):
                add_issue(
                    issues, "BLOCKER", "Wave 1", "Rendered public leak", source,
                    line_number(content, m.start()), msg,
                    "Fix immediately. Public pages must not expose Python/Jinja internals or raw template syntax.",
                )

    id_set = set(ids)

    for a in anchors:
        href = (a.href or "").strip()
        text = a.text or a.attrs.get("aria-label") or a.attrs.get("title") or ""

        if not text and not a.attrs.get("aria-label") and not a.attrs.get("title"):
            add_issue(
                issues, "MEDIUM", "Wave 1", "CTA accessibility", source, a.line,
                "Anchor has no visible text, aria-label, or title.",
                "Add accessible text/aria-label.",
            )

        if href in {"", "#", "javascript:void(0)", "javascript:;"}:
            data_action = " ".join(f"{k}={v}" for k, v in a.attrs.items() if k.startswith("data-"))
            if not data_action:
                sev = "HIGH" if full_page or rendered else "LOW"
                add_issue(
                    issues, sev, "Wave 1", "CTA contract", source, a.line,
                    f"Anchor '{text or '[no text]'}' has dead/ambiguous href: {href!r}.",
                    "Give this CTA a real route, matching section anchor, or explicit JS data action.",
                )

        if href.startswith("#") and href != "#":
            frag = urllib.parse.unquote(href[1:])
            if frag and frag not in id_set and full_page:
                add_issue(
                    issues, "HIGH", "Wave 1", "Anchor contract", source, a.line,
                    f"Anchor '{text or href}' points to missing section id: #{frag}.",
                    "Add the matching id to the target section or correct the href.",
                )

    for b in buttons:
        label = b.text or b.attrs.get("aria-label") or b.attrs.get("title") or ""
        if not label:
            add_issue(
                issues, "MEDIUM", "Wave 1", "CTA accessibility", source, b.line,
                "Button has no visible text, aria-label, or title.",
                "Add accessible label text.",
            )

        if "type" not in b.attrs:
            add_issue(
                issues, "LOW", "Wave 1", "Button semantics", source, b.line,
                f"Button '{label or '[no label]'}' is missing type attribute.",
                "Use type='button' for JS buttons and type='submit' only for form submission.",
            )

        data_attrs = " ".join(f"{k}={v}" for k, v in b.attrs.items() if k.startswith("data-"))
        is_ctaish = re.search(r"\b(donate|sponsor|checkout|share|start|setup|launch|save|export)\b", label + " " + b.cls, re.I)
        if is_ctaish and full_page and not data_attrs and b.attrs.get("type") != "submit":
            add_issue(
                issues, "MEDIUM", "Wave 1", "CTA contract", source, b.line,
                f"CTA-like button '{label}' has no data action and is not submit.",
                "Confirm JS binds this button by class/id. Prefer explicit data-ff-action for launch-critical CTAs.",
            )

    for f in forms:
        action = f.attrs.get("action", "")
        method = f.attrs.get("method", "")
        form_id = f.attrs.get("id", "")
        data_attrs = " ".join(f"{k}={v}" for k, v in f.attrs.items() if k.startswith("data-"))

        if full_page and not action and not data_attrs:
            add_issue(
                issues, "HIGH", "Wave 1", "Form contract", source, f.line,
                f"Form '{form_id or '[no id]'}' has no action and no explicit data action.",
                "Give the form a backend action or explicit JS data contract.",
            )

        if action and method.lower() not in {"post", "get"}:
            add_issue(
                issues, "MEDIUM", "Wave 1", "Form contract", source, f.line,
                f"Form '{form_id or '[no id]'}' has action but missing/invalid method.",
                "Use method='post' for writes and method='get' for search/filter/navigation.",
            )

    cta_texts = []
    for e in anchors + buttons:
        t = clean_text(e.text or e.attrs.get("aria-label") or e.attrs.get("title") or "")
        if re.search(r"\b(donate|sponsor|checkout|start|fundraiser|share|save|launch|setup)\b", t, re.I):
            cta_texts.append(t.lower())

    cta_counts = Counter(cta_texts)
    if full_page:
        for label, count in cta_counts.items():
            threshold = 3 if re.search(r"\bdonate\b|\bsponsor\b", label, re.I) else 4
            if count > threshold:
                add_issue(
                    issues, "MEDIUM", "Wave 1", "CTA hierarchy", source, None,
                    f"CTA label appears {count} times: '{label}'.",
                    "Reduce repeated CTAs or give each page zone a clearer action job.",
                )

    all_cta = " ".join(
        [a.text + " " + a.href for a in anchors] +
        [b.text + " " + b.cls + " " + " ".join(b.attrs.values()) for b in buttons]
    ).lower()

    # Rendered pages are the source of truth for launch CTA contracts.
    # Raw Jinja source can be highly dynamic and should not be failed as a public CTA surface.
    if rendered and full_page and kind == "platform":
        if not re.search(r"\b(start|setup|fundraiser|onboarding)\b", all_cta):
            add_issue(
                issues, "HIGH", "Wave 1", "Platform CTA contract", source, None,
                "Platform page does not clearly expose a Start/Setup/Fundraiser CTA.",
                "Add one primary CTA to onboarding or the canonical start flow.",
            )
        if "/c/connect-atx-elite" not in all_cta and not re.search(r"\b(campaign|demo|example)\b", all_cta):
            add_issue(
                issues, "MEDIUM", "Wave 1", "Platform demo contract", source, None,
                "Platform page does not clearly expose a campaign demo CTA.",
                "Add a secondary CTA to the live campaign demo.",
            )

    if rendered and full_page and kind == "campaign":
        if not re.search(r"\b(donate|checkout|give|support)\b", all_cta):
            add_issue(
                issues, "BLOCKER", "Wave 1", "Campaign donation contract", source, None,
                "Campaign page does not clearly expose a donation/checkout CTA.",
                "Add a primary Donate CTA wired to embedded checkout/session flow.",
            )
        if not re.search(r"\b(sponsor|partner)\b", all_cta):
            add_issue(
                issues, "HIGH", "Wave 1", "Campaign sponsor contract", source, None,
                "Campaign page does not clearly expose a sponsor/partner CTA.",
                "Add a sponsor package path or sponsor CTA wired to sponsor flow.",
            )

    return {
        "kind": kind,
        "full_page": full_page,
        "rendered": rendered,
        "anchor_count": len(anchors),
        "button_count": len(buttons),
        "form_count": len(forms),
        "input_count": len(page["inputs"]),
        "id_count": len(ids),
        "duplicate_ids": duplicate_ids,
        "cta_counts": dict(cta_counts.most_common()),
        "anchors": [element_summary(a) for a in anchors],
        "buttons": [element_summary(b) for b in buttons],
        "forms": [element_summary(f) for f in forms],
    }


def inventory(root: Path, files: List[Path]) -> Dict[str, Any]:
    by_ext = Counter(p.suffix.lower() or p.name for p in files)
    important = defaultdict(int)
    for p in files:
        rp = rel(root, p)
        for prefix in [
            "apps/web/app/templates",
            "apps/web/app/static/css",
            "apps/web/app/static/js",
            "apps/web/app/blueprints",
            "apps/web/app/services",
            "apps/api",
            "scripts",
            "tests",
        ]:
            if rp.startswith(prefix):
                important[prefix] += 1
    return {
        "file_count": len(files),
        "by_ext": dict(by_ext.most_common()),
        "important_counts": dict(sorted(important.items())),
    }




def _ff_is_safe_placeholder_match(path: Path, text: str, start: int, msg: str) -> bool:
    """
    Avoid false positives for legitimate UI placeholder usage.

    Still flag actual public copy that says "placeholder", but ignore:
    - CSS ::placeholder selectors
    - HTML/Jinja placeholder="..." attributes
    - JS .placeholder / placeholder: / setAttribute("placeholder", ...)
    - data-placeholder / aria-placeholder style contracts
    """
    if "Placeholder language" not in msg:
        return False

    suffix = path.suffix.lower()
    ctx = text[max(0, start - 140): start + 180].lower()

    # CSS pseudo-elements/selectors.
    if suffix == ".css" and (
        "::placeholder" in ctx
        or "::-webkit-input-placeholder" in ctx
        or ":-ms-input-placeholder" in ctx
        or "::-ms-input-placeholder" in ctx
        or "::input-placeholder" in ctx
    ):
        return True

    # HTML/Jinja/Svelte/JSX form attributes.
    if "placeholder=" in ctx or "placeholder =" in ctx:
        return True

    # JS input placeholder API / object props.
    if ".placeholder" in ctx:
        return True
    if "placeholder:" in ctx:
        return True
    if 'setattribute("placeholder"' in ctx or "setattribute('placeholder'" in ctx:
        return True

    # Accessibility/data contracts that are not fake public copy.
    if "data-placeholder" in ctx or "aria-placeholder" in ctx:
        return True

    return False

def scan_source_leaks_and_stale(root: Path, files: List[Path], issues: List[Issue]):
    counts = {"source_leak_hits": 0, "stale_hits": 0}
    for p in files:
        rp = rel(root, p)

        # FF_STALE_AUDIT_HYGIENE_V1_START
        # Patch scripts and deprecated templates are not launch-facing product source.
        # They are allowed to mention audit keywords like stub/fake/rescue because
        # their job is to find or fix those markers.
        if (
            rp.startswith("scripts/patches/")
            or rp.startswith("apps/web/app/templates/campaign/deprecated/")
        ):
            continue
        # FF_STALE_AUDIT_HYGIENE_V1_END

        text = read_text(p)
        if not text:
            continue

        # Do not let the audit harness flag its own literal detection patterns.
        if rp.startswith("scripts/audit/"):
            continue

        for pattern, msg in SOURCE_LEAK_PATTERNS:
            for m in re.finditer(pattern, text, re.I):
                counts["source_leak_hits"] += 1
                add_issue(
                    issues, "HIGH", "Wave 0", "Source leak risk", rp, line_number(text, m.start()),
                    msg,
                    "Fix source/template expression so Python reprs cannot reach public pages.",
                )

        for pattern, msg in STALE_PATTERNS:
            for m in re.finditer(pattern, text, re.I):
                if _ff_is_safe_placeholder_match(p, text, m.start(), msg):
                    continue

                sev = "LOW"
                if p.suffix.lower() in {".py", ".html", ".jinja", ".j2", ".js", ".css"}:
                    sev = "MEDIUM"
                if re.search(r"fake|not-wired|stub|placeholder", msg, re.I):
                    sev = "MEDIUM"
                counts["stale_hits"] += 1
                add_issue(
                    issues, sev, "Wave 0", "Stale/demo/fake marker", rp, line_number(text, m.start()),
                    msg,
                    "Confirm intentional. Remove, replace, or quarantine launch-risk placeholder/debug language.",
                )
    return counts


def scan_routes(root: Path, files: List[Path], issues: List[Issue]):
    routes = []
    for p in files:
        if p.suffix.lower() != ".py":
            continue
        text = read_text(p)
        for m in ROUTE_DECORATOR_RE.finditer(text):
            routes.append({"route": m.group("route"), "file": rel(root, p), "line": line_number(text, m.start())})

    route_text = "\n".join(r["route"] for r in routes)
    expected_presence = {}
    for name, candidates in EXPECTED_ROUTES.items():
        present = any(c in route_text for c in candidates)
        expected_presence[name] = present
        if not present:
            add_issue(
                issues, "MEDIUM", "Wave 0", "Route contract", "repo routes", None,
                f"Expected route family not clearly found: {name} ({', '.join(candidates)})",
                "Verify this route exists under the canonical blueprint. If missing, add or document it.",
            )

    return {"routes": routes, "expected_presence": expected_presence}


def scan_assets(root: Path, files: List[Path], issues: List[Issue]):
    css_files = []
    js_files = []
    asset_versions = defaultdict(Counter)

    for p in files:
        rp = rel(root, p)
        if rp.startswith("apps/web/app/static/css"):
            css_files.append(rp)
        if rp.startswith("apps/web/app/static/js"):
            js_files.append(rp)

        text = read_text(p)
        for m in ASSET_VERSION_RE.finditer(text):
            asset_versions[m.group("asset")][m.group("version")] += 1

    for asset, versions in asset_versions.items():
        if len(versions) > 3:
            add_issue(
                issues, "MEDIUM", "Wave 0", "Asset version drift", asset, None,
                f"Asset has many version strings: {', '.join(list(versions)[:8])}",
                "Consolidate asset versioning through one config/env value.",
            )

        stale_versions = [v for v in versions if re.search(r"(rescue|emergency|debug|micropolish|fix|patch)", v, re.I)]
        if stale_versions:
            add_issue(
                issues, "LOW", "Wave 0", "Asset version naming", asset, None,
                f"Asset version includes patch/rescue naming: {', '.join(stale_versions[:8])}",
                "Use calm release names, build hashes, or a single ASSET_V value.",
            )

    if len(css_files) > 8:
        add_issue(
            issues, "LOW", "Wave 0", "CSS authority", "static css inventory", None,
            f"Found {len(css_files)} canonical CSS files.",
            "Confirm canonical CSS authority and remove unused imports before final polish.",
        )

    return {
        "css_files": css_files,
        "js_files": js_files,
        "asset_versions": {k: dict(v) for k, v in asset_versions.items()},
    }


def scan_lifecycle(root: Path, files: List[Path], issues: List[Issue]):
    hits = {"payment_files": [], "email_files": [], "sponsor_files": [], "operator_files": []}

    for p in files:
        rp = rel(root, p)
        text = read_text(p)
        if PAYMENT_HINT_RE.search(text):
            hits["payment_files"].append(rp)
        if EMAIL_HINT_RE.search(text):
            if not rp.startswith("scripts/audit/"):
                hits["email_files"].append(rp)
        if SPONSOR_HINT_RE.search(text):
            hits["sponsor_files"].append(rp)
        if OPERATOR_HINT_RE.search(text):
            hits["operator_files"].append(rp)

    if not hits["payment_files"]:
        add_issue(
            issues, "BLOCKER", "Wave 0", "Payment provider", "repo", None,
            "No payment/checkout/provider implementation signals found.",
            "Add or locate Stripe/PayPal checkout/session/webhook implementation before launch.",
        )

    if not hits["email_files"]:
        add_issue(
            issues, "HIGH", "Wave 0", "Lifecycle messaging", "repo", None,
            "No email/receipt/confirmation implementation signals found.",
            "Add donor receipt, sponsor confirmation, and operator notification flow.",
        )
    else:
        for rp in hits["email_files"]:
            text = read_text(root / rp)
            if re.search(r"\b(stub|outbox|console only|TODO|not wired)\b", text, re.I):
                add_issue(
                    issues, "MEDIUM", "Wave 0", "Lifecycle messaging", rp, None,
                    "Email-related file contains stub/outbox/TODO/not-wired signals.",
                    "Confirm production email delivery is configured; donor/sponsor follow-up should not be outbox-only.",
                )

    return hits


def scan_source_templates(root: Path, files: List[Path], issues: List[Issue]):
    results = {}
    for p in files:
        rp = rel(root, p)
        if p.suffix.lower() not in {".html", ".jinja", ".j2", ".svelte", ".tsx"}:
            continue
        if "templates" not in p.parts and "routes" not in p.parts and "components" not in p.parts:
            continue

        text = read_text(p)
        full = is_full_page_template(p, root)
        page = parse_page(rp, text)
        results[rp] = scan_page_contract(page, text, issues, rendered=False, full_page=full)
    return results


def scan_rendered_urls(base_url: str, live_urls: List[str], skip_network: bool, issues: List[Issue]):
    if skip_network:
        return {}

    urls = [normalize_url(base_url, p) for p in RENDER_URLS_DEFAULT] + live_urls
    ordered = []
    seen = set()
    for url in urls:
        if url not in seen:
            ordered.append(url)
            seen.add(url)

    results = {}
    for url in ordered:
        content, status, error = fetch_url(url)

        if error and content is None:
            add_issue(
                issues, "MEDIUM", "Wave 1", "Rendered page fetch", url, None,
                f"Could not fetch rendered page: {error}",
                "Start local Flask app or verify the live URL.",
            )
            results[url] = {"status": status, "error": error}
            continue

        protected_operator_route = (
            status in {401, 403}
            and ("/platform/dashboard" in url or url.rstrip("/").endswith("/dashboard"))
        )

        if status and status >= 400 and not protected_operator_route:
            add_issue(
                issues, "HIGH", "Wave 1", "Rendered page status", url, None,
                f"Rendered page returned HTTP {status}.",
                "Fix route/auth/redirect/deployment behavior before launch.",
            )

        content = content or ""
        page = parse_page(url, content)

        # A protected dashboard returning 401/403 is a valid operator-access contract.
        # Do not run marketing CTA checks against an access-denied response.
        result = scan_page_contract(
            page,
            content,
            issues,
            rendered=True,
            full_page=not protected_operator_route,
        )
        if protected_operator_route:
            result["protected_operator_route"] = True
        result["status"] = status
        result["bytes"] = len(content.encode("utf-8", errors="replace"))
        results[url] = result

    return results


def scan_js_selectors(root: Path, files: List[Path], issues: List[Issue]):
    html_pool = ""
    selectors = []

    for p in files:
        if p.suffix.lower() in {".html", ".jinja", ".j2", ".svelte", ".tsx"}:
            html_pool += "\n" + read_text(p)

    for p in files:
        if p.suffix.lower() not in {".js", ".ts", ".tsx", ".svelte"}:
            continue
        text = read_text(p)
        rp = rel(root, p)

        # FF_JS_OPTIONAL_INTEL_SKIP_V1_START
        # Optional campaign intel island. The launch pages do not render
        # #ffCampaignIntel, so this script is not part of the required
        # public interaction contract.
        if rp == "apps/web/app/static/js/ff-campaign-intel.js":
            continue
        # FF_JS_OPTIONAL_INTEL_SKIP_V1_END
        for m in SELECTOR_RE.finditer(text):
            selector = m.group("selector") or ""
            id_lookup = m.group("id") or ""
            raw = selector or f"#{id_lookup}"
            line = line_number(text, m.start())
            selectors.append({"file": rp, "line": line, "selector": raw})

            if id_lookup:
                if f'id="{id_lookup}"' not in html_pool and f"id='{id_lookup}'" not in html_pool:
                    add_issue(
                        issues, "LOW", "Wave 1", "JS selector contract", rp, line,
                        f"getElementById('{id_lookup}') has no obvious matching id in templates.",
                        "Verify dynamic render or update selector/template contract.",
                    )
            elif selector.startswith("#") and re.match(r"^#[A-Za-z][\w:-]*$", selector):
                sid = selector[1:]
                if f'id="{sid}"' not in html_pool and f"id='{sid}'" not in html_pool:
                    add_issue(
                        issues, "LOW", "Wave 1", "JS selector contract", rp, line,
                        f"querySelector('{selector}') has no obvious matching id in templates.",
                        "Verify dynamic render or update selector/template contract.",
                    )
            elif selector.startswith(".") and re.match(r"^\.[A-Za-z][\w:-]*$", selector):
                cls = selector[1:]
                if cls not in html_pool:
                    add_issue(
                        issues, "LOW", "Wave 1", "JS selector contract", rp, line,
                        f"querySelector('{selector}') has no obvious matching class in templates.",
                        "Verify dynamic render or update selector/template contract.",
                    )

    return {"selectors": selectors}


def markdown_table(headers, rows):
    def cell(v):
        s = str(v if v is not None else "")
        return s.replace("\n", " ").replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(out)


def render_report(data):
    issues = [Issue(**x) for x in data["issues"]]
    counts = Counter(i.severity for i in issues)
    by_area = Counter(i.area for i in issues)
    by_wave = Counter(i.wave for i in issues)

    lines = []
    lines.append("# FutureFunded Launch Contract Audit")
    lines.append("")
    lines.append(f"- **Audit version:** `{data['audit_version']}`")
    lines.append(f"- **Generated:** `{data['generated_at']}`")
    lines.append(f"- **Repo root:** `{data['root']}`")
    lines.append(f"- **Backups included:** `{data['include_backups']}`")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(markdown_table(
        ["Severity", "Count"],
        [[sev, counts.get(sev, 0)] for sev in ["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]],
    ))
    lines.append("")

    if counts.get("BLOCKER"):
        lines.append("> 🚨 **Launch blocker present.** Fix BLOCKER items before any more visual polish.")
    elif counts.get("HIGH"):
        lines.append("> ⚠️ **High-priority launch risks present.** Fix before demo/sales confidence.")
    else:
        lines.append("> ✅ No blocker/high issues detected by this focused audit.")
    lines.append("")

    lines.append("## Wave Counts")
    lines.append("")
    lines.append(markdown_table(["Wave", "Issue count"], by_wave.most_common()))
    lines.append("")

    lines.append("## Area Counts")
    lines.append("")
    lines.append(markdown_table(["Area", "Issue count"], by_area.most_common(20)))
    lines.append("")

    inv = data["inventory"]
    lines.append("## Wave 0 — Repo Truth Map")
    lines.append("")
    lines.append(f"- **Canonical text files scanned:** `{inv.get('file_count', 0)}`")
    lines.append("")
    for k, v in inv.get("important_counts", {}).items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")

    routes = data.get("routes", {}).get("routes", [])
    lines.append("### Route Inventory")
    lines.append("")
    if routes:
        lines.append(markdown_table(["Route", "File", "Line"], [[r["route"], r["file"], r["line"]] for r in routes[:140]]))
        if len(routes) > 140:
            lines.append(f"\n_Only first 140 routes shown of {len(routes)}._")
    else:
        lines.append("_No route decorators detected._")
    lines.append("")

    expected = data.get("routes", {}).get("expected_presence", {})
    lines.append("### Expected Route Families")
    lines.append("")
    lines.append(markdown_table(
        ["Contract", "Detected"],
        [[k, "✅ yes" if v else "⚠️ not obvious"] for k, v in expected.items()],
    ))
    lines.append("")

    assets = data.get("assets", {})
    lines.append("### Static Asset Inventory")
    lines.append("")
    lines.append(f"- **Canonical CSS files:** `{len(assets.get('css_files', []))}`")
    lines.append(f"- **Canonical JS files:** `{len(assets.get('js_files', []))}`")
    lines.append("")
    for f in assets.get("css_files", [])[:30]:
        lines.append(f"- `{f}`")
    lines.append("")

    lifecycle = data.get("lifecycle", {})
    lines.append("### Provider / Lifecycle Signals")
    lines.append("")
    lines.append(markdown_table(
        ["Signal", "Files detected"],
        [
            ["Payment/checkout", len(lifecycle.get("payment_files", []))],
            ["Email/receipt/confirmation", len(lifecycle.get("email_files", []))],
            ["Sponsor", len(lifecycle.get("sponsor_files", []))],
            ["Operator/dashboard/onboarding", len(lifecycle.get("operator_files", []))],
        ],
    ))
    lines.append("")

    rendered = data.get("rendered_pages", {})
    lines.append("## Wave 1 — Rendered Button / Link / Form Sweep")
    lines.append("")
    if rendered:
        rows = []
        for source, result in rendered.items():
            rows.append([
                source,
                result.get("status", ""),
                result.get("kind", ""),
                result.get("anchor_count", 0),
                result.get("button_count", 0),
                result.get("form_count", 0),
                len(result.get("duplicate_ids", {}) or {}),
            ])
        lines.append(markdown_table(["Page", "HTTP", "Kind", "Anchors", "Buttons", "Forms", "Duplicate IDs"], rows))
    else:
        lines.append("_No rendered pages fetched._")
    lines.append("")

    lines.append("## Prioritized Findings")
    lines.append("")
    sorted_issues = sorted(issues, key=issue_sort_key)
    if not sorted_issues:
        lines.append("_No issues detected._")
    else:
        rows = []
        for i, issue in enumerate(sorted_issues[:250], start=1):
            loc = issue.location + (f":{issue.line}" if issue.line else "")
            rows.append([i, issue.severity, issue.wave, issue.area, loc, issue.message, issue.recommendation])
        lines.append(markdown_table(
            ["#", "Severity", "Wave", "Area", "Location", "Finding", "Recommendation"],
            rows,
        ))
        if len(sorted_issues) > 250:
            lines.append(f"\n_Only first 250 findings shown of {len(sorted_issues)}. See JSON for full data._")
    lines.append("")

    lines.append("## Suggested Next Moves")
    lines.append("")
    lines.append("1. Fix true rendered-page `BLOCKER` findings first.")
    lines.append("2. Fix full-page CTA/form/anchor `HIGH` findings next.")
    lines.append("3. Confirm lifecycle messaging is provider-backed, not outbox-only.")
    lines.append("4. Re-run this focused audit until counts stabilize.")
    lines.append("")

    return "\n".join(lines)


def write_outputs(root: Path, output_dir: Path, data):
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"ff_launch_contract_audit_{stamp}.json"
    md_path = output_dir / f"ff_launch_contract_audit_{stamp}.md"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_report(data), encoding="utf-8")
    return md_path, json_path


def parse_args():
    parser = argparse.ArgumentParser(description="FutureFunded Wave 0 + Wave 1 launch contract audit v2.")
    parser.add_argument("--root", default=".", help="Repo root.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Local base URL.")
    parser.add_argument("--live-url", action="append", default=[], help="Additional live URL. Repeatable.")
    parser.add_argument("--skip-network", action="store_true", help="Skip rendered URL checks.")
    parser.add_argument("--include-backups", action="store_true", help="Include tmp/backups/quarantine folders.")
    parser.add_argument("--output-dir", default="audit_outputs", help="Report output directory.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on BLOCKER/HIGH.")
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    output_dir = root / args.output_dir

    if not root.exists():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        return 2

    print(f"FutureFunded Launch Contract Audit • {AUDIT_VERSION}")
    print(f"Repo root: {root}")
    print(f"Include backups: {args.include_backups}")
    print("Scanning canonical files...")

    issues: List[Issue] = []
    files = collect_files(root, args.include_backups)

    inv = inventory(root, files)
    stale = scan_source_leaks_and_stale(root, files, issues)
    routes = scan_routes(root, files, issues)
    assets = scan_assets(root, files, issues)
    lifecycle = scan_lifecycle(root, files, issues)

    print("Scanning source templates/buttons...")
    source_pages = scan_source_templates(root, files, issues)

    print("Scanning JS selector contracts...")
    selectors = scan_js_selectors(root, files, issues)

    print("Fetching rendered pages...")
    rendered_pages = scan_rendered_urls(args.base_url, args.live_url, args.skip_network, issues)

    data = {
        "audit_version": AUDIT_VERSION,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "root": str(root),
        "include_backups": args.include_backups,
        "base_url": args.base_url,
        "live_urls": args.live_url,
        "inventory": inv,
        "stale_scan": stale,
        "routes": routes,
        "assets": assets,
        "lifecycle": lifecycle,
        "source_pages": source_pages,
        "rendered_pages": rendered_pages,
        "selectors": selectors,
        "issues": [asdict(i) for i in sorted(issues, key=issue_sort_key)],
    }

    md_path, json_path = write_outputs(root, output_dir, data)

    counts = Counter(i.severity for i in issues)
    print("")
    print("Audit complete.")
    print(f"Markdown report: {md_path}")
    print(f"JSON report:     {json_path}")
    print("")
    print("Severity summary:")
    for sev in ["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]:
        print(f"  {sev:<8} {counts.get(sev, 0)}")

    if args.strict and (counts.get("BLOCKER", 0) or counts.get("HIGH", 0)):
        print("")
        print("Strict mode failed: BLOCKER/HIGH findings exist.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

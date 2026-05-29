#!/usr/bin/env python3
"""
FutureFunded functional funnel audit.

This validates whether the product is merely pretty or actually sellable:
- critical routes exist
- pages load
- dashboard auth works
- CTAs/copy exist
- internal links avoid 404s
- forms have action/method/named fields
- upload forms use multipart/form-data
- payment/donation/sponsor/webhook routes are discoverable
- email/follow-up implementation references exist
- key provider env vars are configured
- white-label hard-coded copy risks are surfaced

This does not create live charges.
Run sandbox Stripe/PayPal tests separately after this passes.
"""

from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402


PASS: list[tuple[str, str]] = []
WARN: list[tuple[str, str]] = []
FAIL: list[tuple[str, str]] = []


def ok(name: str, detail: str = "") -> None:
    PASS.append((name, detail))
    print(f"✅ {name:<52} {detail}")


def warn(name: str, detail: str = "") -> None:
    WARN.append((name, detail))
    print(f"⚠️  {name:<52} {detail}")


def fail(name: str, detail: str = "") -> None:
    FAIL.append((name, detail))
    print(f"❌ {name:<52} {detail}")


class FunnelHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.forms: list[dict] = []
        self.current_form: dict | None = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "a":
            href = attrs.get("href", "").strip()
            if href:
                self.links.append(href)

        if tag == "form":
            self.current_form = {
                "action": attrs.get("action", "").strip(),
                "method": attrs.get("method", "GET").upper(),
                "enctype": attrs.get("enctype", "").strip(),
                "fields": [],
                "submit_count": 0,
            }
            self.forms.append(self.current_form)

        if tag in {"input", "textarea", "select"} and self.current_form is not None:
            name = attrs.get("name", "").strip()
            input_type = attrs.get("type", "").strip().lower()
            self.current_form["fields"].append((tag, name, input_type))

            if input_type == "submit":
                self.current_form["submit_count"] += 1

        if tag == "button" and self.current_form is not None:
            button_type = attrs.get("type", "").strip().lower()
            if button_type in {"", "submit"}:
                self.current_form["submit_count"] += 1

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None


def parse_html(html: str) -> FunnelHTMLParser:
    parser = FunnelHTMLParser()
    parser.feed(html)
    return parser


def internal_path(href: str) -> str | None:
    if not href or href.startswith("#"):
        return None

    if href.startswith(("mailto:", "tel:", "sms:", "javascript:")):
        return None

    parsed = urlparse(href)

    if parsed.scheme and parsed.netloc:
        return None

    path = parsed.path or "/"

    if not path.startswith("/"):
        return None

    return path + (f"?{parsed.query}" if parsed.query else "")


def discover_routes(app, keywords: list[str]) -> list[str]:
    hits: list[str] = []

    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        haystack = f"{rule} {rule.endpoint} {methods}".lower()

        if any(keyword in haystack for keyword in keywords):
            hits.append(f"{rule} -> {rule.endpoint} [{methods}]")

    return sorted(hits)


def env_any(names: list[str]) -> bool:
    return any(bool(os.getenv(name, "").strip()) for name in names)


def scan_file_text(paths: list[Path], pattern: str) -> list[str]:
    rx = re.compile(pattern, re.I)
    hits: list[str] = []

    for path in paths:
        if not path.exists() or not path.is_file():
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if rx.search(text):
            hits.append(str(path.relative_to(REPO_ROOT)))

    return sorted(set(hits))


def collect_source_files() -> list[Path]:
    roots = [
        REPO_ROOT / "apps/web/app",
        REPO_ROOT / "apps/web",
    ]

    files: list[Path] = []

    for root in roots:
        if not root.exists():
            continue

        for pattern in ("*.py", "*.html", "*.txt", "*.jinja", "*.j2"):
            files.extend(root.rglob(pattern))

    return sorted(set(files))


def main() -> int:
    token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()

    print("\nFutureFunded functional funnel audit")
    print("=" * 76)

    app = create_app()
    client = app.test_client()

    routes = {str(rule) for rule in app.url_map.iter_rules()}

    expected_routes = [
        "/platform",
        "/platform/",
        "/platform/onboarding",
        "/platform/login",
        "/platform/dashboard",
        "/platform/media/upload",
        "/c/<slug>",
    ]

    print("\nRoute contract")
    print("-" * 76)

    for route in expected_routes:
        if route in routes:
            ok(f"route registered {route}")
        else:
            fail(f"route missing {route}")

    route_groups = {
        "payment/fundraising routes": [
            "donat",
            "sponsor",
            "checkout",
            "stripe",
            "paypal",
            "payment",
        ],
        "webhook routes": [
            "webhook",
            "stripe",
            "paypal",
        ],
        "media/upload routes": [
            "upload",
            "media",
        ],
        "email-related routes": [
            "mail",
            "email",
            "receipt",
            "thank",
        ],
    }

    for label, keywords in route_groups.items():
        hits = discover_routes(app, keywords)

        if hits:
            ok(f"{label} discovered", f"{len(hits)} route(s)")
            for item in hits[:18]:
                print(f"   • {item}")
        else:
            if label == "email-related routes":
                warn(f"{label} discovered", "none obvious; email may be service/internal only")
            else:
                fail(f"{label} discovered", "none found")

    print("\nPage load contract")
    print("-" * 76)

    pages = {
        "platform": "/platform/",
        "onboarding": "/platform/onboarding",
        "login": "/platform/login",
        "campaign": "/c/connect-atx-elite",
    }

    html_by_page: dict[str, str] = {}

    for name, path in pages.items():
        res = client.get(path, follow_redirects=False)

        if res.status_code == 200:
            ok(f"{name} loads", f"HTTP {res.status_code}")
            html_by_page[name] = res.get_data(as_text=True)
        else:
            fail(f"{name} loads", f"HTTP {res.status_code}")

    no_auth = client.get("/platform/dashboard", follow_redirects=False)

    if no_auth.status_code in {302, 401, 403}:
        ok("dashboard blocks anonymous users", f"HTTP {no_auth.status_code}")
    else:
        fail("dashboard blocks anonymous users", f"HTTP {no_auth.status_code}")

    if token:
        auth_checks = [
            ("query token", f"/platform/dashboard?token={token}", {}),
            ("operator_token query", f"/platform/dashboard?operator_token={token}", {}),
            ("X-Operator-Token header", "/platform/dashboard", {"X-Operator-Token": token}),
            ("Bearer header", "/platform/dashboard", {"Authorization": f"Bearer {token}"}),
        ]

        for label, path, headers in auth_checks:
            res = client.get(path, headers=headers, follow_redirects=False)

            if res.status_code == 200:
                ok(f"dashboard auth {label}", "HTTP 200")
                html_by_page.setdefault("dashboard", res.get_data(as_text=True))
            else:
                warn(f"dashboard auth {label}", f"HTTP {res.status_code}")
    else:
        warn("dashboard auth", "FF_OPERATOR_ACCESS_TOKEN is not set")

    print("\nCTA/content contract")
    print("-" * 76)

    required_copy = {
        "onboarding": [
            "Save setup",
            "Review summary",
            "Dashboard",
            "Upload",
            "Preview campaign",
            "Open dashboard",
        ],
        "dashboard": [
            "Campaign dashboard",
            "Preview campaign",
            "Edit setup",
            "Campaign performance",
            "Readiness",
            "Next best actions",
            "Open public page",
        ],
        "campaign": [
            "Donate",
            "Sponsor",
            "Become a sponsor",
            "Share",
        ],
    }

    for page, needles in required_copy.items():
        html = html_by_page.get(page, "")

        if not html:
            warn(f"{page} CTA/content scan", "page HTML unavailable")
            continue

        for needle in needles:
            if needle.lower() in html.lower():
                ok(f"{page} CTA/content present", needle)
            else:
                warn(f"{page} CTA/content missing", needle)

    print("\nForm contract")
    print("-" * 76)

    for page, html in html_by_page.items():
        parser = parse_html(html)

        if not parser.forms:
            if page in {"onboarding", "campaign"}:
                warn(f"{page} forms", "no forms found")
            continue

        for index, form in enumerate(parser.forms, start=1):
            action = form["action"] or "(current URL)"
            method = form["method"]
            named_fields = [name for _, name, _ in form["fields"] if name]
            has_file = any(input_type == "file" for _, _, input_type in form["fields"])

            if method in {"GET", "POST"}:
                ok(f"{page} form {index} method", method)
            else:
                fail(f"{page} form {index} method", method)

            if action:
                ok(f"{page} form {index} action", action)
            else:
                warn(f"{page} form {index} action", "blank")

            if named_fields:
                ok(f"{page} form {index} named fields", f"{len(named_fields)} field(s)")
            else:
                fail(f"{page} form {index} named fields", "none")

            if form["submit_count"] > 0:
                ok(f"{page} form {index} submit control", f"{form['submit_count']} submit control(s)")
            else:
                warn(f"{page} form {index} submit control", "none detected")

            if has_file:
                if "multipart/form-data" in form["enctype"]:
                    ok(f"{page} upload form enctype", "multipart/form-data")
                else:
                    fail(f"{page} upload form enctype", form["enctype"] or "(missing)")

    print("\nInternal link contract")
    print("-" * 76)

    checked: set[tuple[str, str]] = set()

    for page, html in html_by_page.items():
        parser = parse_html(html)

        for href in parser.links:
            path = internal_path(href)

            if not path:
                continue

            if path.startswith("/platform/dashboard") and token and "token=" not in path and "operator_token=" not in path:
                path = f"/platform/dashboard?token={token}"

            key = (page, path)

            if key in checked:
                continue

            checked.add(key)

            try:
                res = client.get(path, follow_redirects=False)
            except Exception as exc:
                fail(f"{page} internal link", f"{href} -> raised {exc.__class__.__name__}: {exc}")
                continue

            if res.status_code < 400:
                ok(f"{page} internal link", f"{href} -> HTTP {res.status_code}")
            elif res.status_code in {401, 403} and "/dashboard" in path:
                ok(f"{page} protected internal link", f"{href} -> HTTP {res.status_code}")
            else:
                fail(f"{page} internal link", f"{href} -> HTTP {res.status_code}")

    print("\nProvider/env readiness")
    print("-" * 76)

    config_checks = [
        ("Stripe publishable key", ["STRIPE_PUBLIC_KEY", "STRIPE_PUBLISHABLE_KEY"]),
        ("Stripe secret key", ["STRIPE_SECRET_KEY"]),
        ("Stripe webhook secret", ["STRIPE_WEBHOOK_SECRET"]),
        ("PayPal client id", ["PAYPAL_CLIENT_ID"]),
        ("PayPal client secret", ["PAYPAL_CLIENT_SECRET"]),
        ("Mail server", ["MAIL_SERVER", "SMTP_HOST"]),
        ("Mail username", ["MAIL_USERNAME", "SMTP_USERNAME"]),
        ("Mail password", ["MAIL_PASSWORD", "SMTP_PASSWORD"]),
        ("Default sender", ["MAIL_DEFAULT_SENDER", "DEFAULT_FROM_EMAIL", "MAIL_FROM"]),
        ("Public base URL", ["PUBLIC_BASE_URL", "FF_PUBLIC_BASE_URL", "APP_PUBLIC_URL"]),
    ]

    for label, names in config_checks:
        if env_any(names):
            ok(label, "configured")
        else:
            warn(label, f"missing env: {' or '.join(names)}")

    print("\nSource implementation discovery")
    print("-" * 76)

    source_files = collect_source_files()

    email_hits = scan_file_text(
        source_files,
        r"(mail\.send|Message\(|send_email|receipt|thank.you|thank you|sponsor confirmation|donor|donation|sponsor)",
    )

    if email_hits:
        ok("email/follow-up references", f"{len(email_hits)} file(s)")
        for item in email_hits[:22]:
            print(f"   • {item}")
    else:
        fail("email/follow-up references", "no obvious donor/sponsor follow-up implementation found")

    webhook_hits = scan_file_text(
        source_files,
        r"(checkout\.session\.completed|payment_intent\.succeeded|stripe\.Webhook|webhook|paypal)",
    )

    if webhook_hits:
        ok("payment webhook references", f"{len(webhook_hits)} file(s)")
        for item in webhook_hits[:22]:
            print(f"   • {item}")
    else:
        fail("payment webhook references", "no obvious Stripe/PayPal webhook implementation found")

    print("\nWhite-label risk scan")
    print("-" * 76)

    whitelist_scan_roots = [
        REPO_ROOT / "apps/web/app/templates",
        REPO_ROOT / "apps/web/app/static/css",
        REPO_ROOT / "apps/web/app/blueprints",
        REPO_ROOT / "apps/web/app/routes",
    ]

    white_label_files: list[Path] = []

    for root in whitelist_scan_roots:
        if root.exists():
            for pattern in ("*.py", "*.html", "*.jinja", "*.j2", "*.css"):
                white_label_files.extend(root.rglob(pattern))

    quarantined_white_label_files = [
        path
        for path in white_label_files
        if "campaign/deprecated" in path.as_posix()
    ]

    white_label_files = [
        path
        for path in white_label_files
        if "campaign/deprecated" not in path.as_posix()
    ]

    if quarantined_white_label_files:
        ok(
            "deprecated campaign templates quarantined",
            f"{len(quarantined_white_label_files)} file(s) excluded from active white-label risk",
        )

    hardcoded_terms = [
        "Connect ATX Elite",
        "connect-atx-elite",
        "Austin, TX",
        "sponsor@futurefunded.com",
    ]

    for term in hardcoded_terms:
        hits = scan_file_text(white_label_files, re.escape(term))

        if hits:
            warn(f"white-label hardcoded term: {term}", f"{len(hits)} file(s)")
            for item in hits[:14]:
                print(f"   • {item}")
        else:
            ok(f"white-label hardcoded term clear: {term}")

    print("\n" + "=" * 76)
    print(f"PASS: {len(PASS)}  WARN: {len(WARN)}  FAIL: {len(FAIL)}")

    if WARN:
        print("\nWarnings to review:")
        for name, detail in WARN:
            print(f"⚠️  {name}: {detail}")

    if FAIL:
        print("\nFailures to fix before calling this sellable:")
        for name, detail in FAIL:
            print(f"❌ {name}: {detail}")
        return 1

    print("\n✅ FUNCTIONAL FUNNEL AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

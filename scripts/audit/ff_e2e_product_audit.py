#!/usr/bin/env python3
"""
FutureFunded E2E Product Audit

Purpose:
- Product-level launch QA across public, campaign, operator, payments, ledger, and assets.
- Uses Python stdlib only.
- Does not perform real charges.
- Optional --create-checkout only creates a Stripe Checkout session; it does not pay.

Examples:
  python3 scripts/audit/ff_e2e_product_audit.py
  python3 scripts/audit/ff_e2e_product_audit.py --base-url https://getfuturefunded.com
  python3 scripts/audit/ff_e2e_product_audit.py --base-url https://getfuturefunded.com --run-visual --run-buttons
  python3 scripts/audit/ff_e2e_product_audit.py --create-checkout --run-visual --run-buttons --run-money
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import html
import json
import os
import re
import ssl
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:5000"
DEFAULT_CAMPAIGN = "connect-atx-elite"
OUT_DIR = Path("audit_outputs/e2e-product/latest")
TOKEN_FILES = [
    Path("/tmp/ff_operator_token.private"),
    Path("/tmp/ff_operator_token"),
]


@dataclasses.dataclass
class AuditResult:
    status: str
    area: str
    code: str
    message: str
    detail: str = ""


@dataclasses.dataclass
class HttpResult:
    method: str
    url: str
    status: int
    headers: dict[str, str]
    body: bytes
    elapsed_ms: int
    error: str = ""

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", self.headers.get("Content-Type", ""))


class SimpleHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag.lower(), {k.lower(): (v or "") for k, v in attrs}))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self.text_parts.append(data)

    @property
    def visible_text(self) -> str:
        text = " ".join(part.strip() for part in self.text_parts if part.strip())
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    def find_all(self, tag: str | None = None) -> list[tuple[str, dict[str, str]]]:
        if tag is None:
            return self.tags
        return [(t, a) for t, a in self.tags if t == tag.lower()]

    def attr_contains(self, tag: str, attr: str, needle: str) -> bool:
        needle_l = needle.lower()
        for t, attrs in self.find_all(tag):
            if needle_l in attrs.get(attr.lower(), "").lower():
                return True
        return False

    def has_selector_hint(self, needle: str) -> bool:
        needle_l = needle.lower()
        for _, attrs in self.tags:
            haystack = " ".join(
                str(v) for k, v in attrs.items()
                if k in {"class", "id"} or k.startswith("data-") or k in {"href", "src", "name", "type", "aria-label"}
            ).lower()
            if needle_l in haystack:
                return True
        return False


class Auditor:
    def __init__(self, base_url: str, campaign_slug: str, operator_token: str, args: argparse.Namespace) -> None:
        self.base_url = base_url.rstrip("/")
        self.origin = urllib.parse.urlparse(self.base_url).netloc
        self.campaign_slug = campaign_slug
        self.operator_token = operator_token.strip()
        self.args = args
        self.results: list[AuditResult] = []
        self.http_cache: dict[str, HttpResult] = {}
        self.ssl_context = ssl.create_default_context()
        if args.insecure:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

    # ---------------------------
    # Output helpers
    # ---------------------------

    def redact(self, value: Any) -> str:
        text = str(value or "")
        if self.operator_token:
            text = text.replace(self.operator_token, "[TOKEN]")
        return text

    def add(self, status: str, area: str, code: str, message: str, detail: str = "") -> None:
        result = AuditResult(
            status=status,
            area=area,
            code=code,
            message=self.redact(message),
            detail=self.redact(detail),
        )
        self.results.append(result)
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(status, status)
        print(f"{icon} {area} {code} — {result.message}")
        if result.detail and self.args.verbose:
            print(f"    {result.detail}")

    # ---------------------------
    # HTTP helpers
    # ---------------------------

    def absolute_url(self, path_or_url: str) -> str:
        return urllib.parse.urljoin(self.base_url + "/", path_or_url)

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        json_data: Any | None = None,
        form_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 20,
        cache: bool = False,
    ) -> HttpResult:
        url = self.absolute_url(path_or_url)
        key = f"{method.upper()} {url} {json.dumps(json_data, sort_keys=True, default=str) if json_data is not None else ''}"

        if cache and key in self.http_cache:
            return self.http_cache[key]

        data: bytes | None = None
        final_headers = {
            "User-Agent": "FutureFunded-E2E-Product-Audit/1.0",
            **(headers or {}),
        }

        if json_data is not None:
            data = json.dumps(json_data).encode("utf-8")
            final_headers.setdefault("Content-Type", "application/json")
        elif form_data is not None:
            data = urllib.parse.urlencode(form_data).encode("utf-8")
            final_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        req = urllib.request.Request(url, data=data, headers=final_headers, method=method.upper())
        started = time.perf_counter()

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=self.ssl_context) as response:
                body = response.read()
                elapsed = int((time.perf_counter() - started) * 1000)
                result = HttpResult(
                    method=method.upper(),
                    url=url,
                    status=int(response.status),
                    headers={k.lower(): v for k, v in response.headers.items()},
                    body=body,
                    elapsed_ms=elapsed,
                )
        except urllib.error.HTTPError as error:
            body = error.read()
            elapsed = int((time.perf_counter() - started) * 1000)
            result = HttpResult(
                method=method.upper(),
                url=url,
                status=int(error.code),
                headers={k.lower(): v for k, v in error.headers.items()},
                body=body,
                elapsed_ms=elapsed,
                error=str(error),
            )
        except Exception as error:
            elapsed = int((time.perf_counter() - started) * 1000)
            result = HttpResult(
                method=method.upper(),
                url=url,
                status=0,
                headers={},
                body=b"",
                elapsed_ms=elapsed,
                error=f"{type(error).__name__}: {error}",
            )

        if cache:
            self.http_cache[key] = result

        return result

    def expect_status(
        self,
        area: str,
        code: str,
        response: HttpResult,
        expected: set[int] | list[int] | tuple[int, ...],
        detail: str = "",
    ) -> bool:
        expected_set = set(expected)
        ok = response.status in expected_set
        if ok:
            self.add("PASS", area, code, f"{response.method} {self.redact(response.url)} -> {response.status} ({response.elapsed_ms}ms)")
        else:
            self.add(
                "FAIL",
                area,
                code,
                f"{response.method} {self.redact(response.url)} expected {sorted(expected_set)} got {response.status}",
                detail or response.text[:900],
            )
        return ok

    # ---------------------------
    # HTML helpers
    # ---------------------------

    def parse_html(self, response: HttpResult) -> SimpleHTML:
        parser = SimpleHTML()
        parser.feed(response.text)
        return parser

    def html_contains(self, area: str, parser: SimpleHTML, needle: str, code: str, *, fail: bool = True) -> bool:
        haystack = parser.visible_text + " " + " ".join(
            " ".join(attrs.values()) for _, attrs in parser.find_all()
        )
        ok = needle.lower() in haystack.lower()
        self.add("PASS" if ok else ("FAIL" if fail else "WARN"), area, code, f"{needle!r} {'found' if ok else 'missing'}")
        return ok

    def find_same_origin_links(self, parser: SimpleHTML) -> list[dict[str, str]]:
        links: list[dict[str, str]] = []
        seen: set[str] = set()

        for _, attrs in parser.find_all("a"):
            href = (attrs.get("href") or "").strip()
            text = re.sub(r"\s+", " ", attrs.get("aria-label", "") or "").strip()

            if not text:
                # HTMLParser does not give nested text per tag; href is enough for audit.
                text = href

            if not href:
                continue
            if href.startswith("#") or re.match(r"^(mailto|tel|javascript):", href, re.I):
                continue
            if re.search(r"(logout|delete|remove|trash|refund)", href, re.I):
                continue

            url = self.absolute_url(href)
            parsed = urllib.parse.urlparse(url)
            if parsed.netloc != self.origin:
                continue
            if url in seen:
                continue

            seen.add(url)
            links.append({"href": href, "url": url, "text": text})

        return links

    # ---------------------------
    # Audit sections
    # ---------------------------

    def audit_routes_and_html(self) -> dict[str, tuple[HttpResult, SimpleHTML]]:
        print("\n▶ Route + HTML contract audit")
        print("-" * 60)

        token_qs = urllib.parse.urlencode({"access_token": self.operator_token}) if self.operator_token else ""
        surfaces: list[tuple[str, str, set[int]]] = [
            ("platform", "/platform/", {200}),
            ("campaign", f"/c/{self.campaign_slug}", {200}),
            ("login", "/platform/login", {200}),
            ("onboarding", "/platform/onboarding", {200}),
            ("dashboard_locked", "/platform/dashboard", {403}),
        ]

        if self.operator_token:
            surfaces.append(("dashboard_operator", f"/platform/dashboard?{token_qs}", {200}))
        else:
            self.add("WARN", "dashboard_operator", "operator_token", "No operator token available; authenticated dashboard route skipped")

        parsed: dict[str, tuple[HttpResult, SimpleHTML]] = {}

        for area, route, expected in surfaces:
            response = self.request("GET", route, cache=True)
            self.expect_status(area, "http_status", response, expected)
            parser = self.parse_html(response)
            parsed[area] = (response, parser)

            if response.status in expected and response.status:
                if "<html" not in response.text.lower():
                    self.add("WARN", area, "html_shape", "Response does not look like full HTML")
                else:
                    self.add("PASS", area, "html_shape", "HTML document returned")

                title_found = bool(re.search(r"<title[^>]*>.*?</title>", response.text, re.I | re.S))
                self.add("PASS" if title_found else "WARN", area, "title", "Title tag present" if title_found else "Title tag missing")

                self.audit_inline_csp_risk(area, response.text)
                self.audit_assets(area, parser)

        return parsed

    def audit_inline_csp_risk(self, area: str, text: str) -> None:
        inline_scripts = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", text, flags=re.I)
        unsafe_inline_scripts = [
            attrs for attrs in inline_scripts
            if not re.search(r'type=["\']application/(json|ld\+json)["\']', attrs, re.I)
        ]
        style_attrs = re.findall(r"\sstyle=[\"'][^\"']+[\"']", text, flags=re.I)

        self.add(
            "PASS" if not unsafe_inline_scripts else "FAIL",
            area,
            "inline_script_csp",
            "No unsafe inline scripts" if not unsafe_inline_scripts else f"{len(unsafe_inline_scripts)} unsafe inline script tag(s)",
        )
        self.add(
            "PASS" if not style_attrs else "FAIL",
            area,
            "inline_style_csp",
            "No inline style attributes" if not style_attrs else f"{len(style_attrs)} inline style attribute(s)",
            " | ".join(style_attrs[:5]),
        )

    def audit_assets(self, area: str, parser: SimpleHTML) -> None:
        assets: list[str] = []

        for _, attrs in parser.find_all("link"):
            href = attrs.get("href", "")
            rel = attrs.get("rel", "")
            if href and ("stylesheet" in rel.lower() or href.endswith(".css") or ".css?" in href):
                assets.append(href)

        for _, attrs in parser.find_all("script"):
            src = attrs.get("src", "")
            if src:
                assets.append(src)

        same_origin_assets = []
        for asset in assets:
            url = self.absolute_url(asset)
            parsed = urllib.parse.urlparse(url)
            if parsed.netloc == self.origin:
                same_origin_assets.append(url)

        if same_origin_assets:
            self.add("PASS", area, "asset_inventory", f"{len(same_origin_assets)} same-origin CSS/JS asset(s)")
        else:
            self.add("WARN", area, "asset_inventory", "No same-origin CSS/JS assets discovered")

        for url in same_origin_assets[:30]:
            response = self.request("GET", url, timeout=20, cache=True)
            if 200 <= response.status < 400:
                self.add("PASS", area, "asset_load", f"{self.redact(url)} -> {response.status}")
            else:
                self.add("FAIL", area, "asset_load", f"{self.redact(url)} -> {response.status}", response.text[:500])

    def audit_surface_contracts(self, parsed: dict[str, tuple[HttpResult, SimpleHTML]]) -> None:
        print("\n▶ Product surface contract audit")
        print("-" * 60)

        contracts = {
            "platform": [
                ("Launch a premium fundraising page", "home_copy_contract", False),
                ("platform-home.css", "home_css_link", True),
                ("ff-app.js", "home_js_link", True),
                ("Start setup", "home_setup_copy", False),
            ],
            "campaign": [
                ("campaign.css", "campaign_css_link", True),
                ("ff-campaign.js", "campaign_js_link", True),
                ("data-ff-open-checkout", "donate_hook", True),
                ("data-ff-amount-button", "amount_hook", True),
                ("data-ff-custom-amount", "custom_amount_hook", True),
                ("data-ff-open-sponsor", "sponsor_hook", False),
                ("data-ff-share", "share_hook", False),
            ],
            "login": [
                ("login.css", "login_css_link", True),
                ("ff-login.js", "login_js_link", False),
                ("password", "password_input", True),
            ],
            "onboarding": [
                ("onboarding.css", "onboarding_css_link", True),
                ("form", "form_contract", False),
            ],
            "dashboard_locked": [
                ("Protected dashboard", "locked_copy", False),
                ("platform/login", "locked_login_link", False),
                ("platform/onboarding", "locked_setup_link", False),
            ],
            "dashboard_operator": [
                ("dashboard.css", "dashboard_css_link", True),
                ("ff-operator-dashboard.js", "dashboard_js_link", False),
                ("ledger/export.csv", "ledger_export_link", True),
                ("data-ff-export-href", "ledger_export_href_contract", True),
            ],
        }

        for area, checks in contracts.items():
            if area not in parsed:
                continue
            _, parser = parsed[area]
            raw = " ".join(
                [parser.visible_text]
                + [
                    " ".join(
                        [tag]
                        + [
                            f"{key}={value}" if value else key
                            for key, value in attrs.items()
                        ]
                    )
                    for tag, attrs in parser.find_all()
                ]
            )
            for needle, code, required in checks:
                ok = needle.lower() in raw.lower()
                self.add("PASS" if ok else ("FAIL" if required else "WARN"), area, code, f"{needle!r} {'present' if ok else 'missing'}")

        if "dashboard_operator" in parsed and self.operator_token:
            _, parser = parsed["dashboard_operator"]
            export_links = [
                attrs.get("href", "")
                for _, attrs in parser.find_all("a")
                if "ledger/export.csv" in attrs.get("href", "")
            ]
            if not export_links:
                self.add("FAIL", "dashboard_operator", "export_link_present", "Ledger export link missing")
            else:
                tokenized = any("operator_token=" in href or "access_token=" in href or "token=" in href for href in export_links)
                self.add("PASS" if tokenized else "FAIL", "dashboard_operator", "export_link_tokenized", "Ledger export link carries operator token" if tokenized else "Ledger export link missing operator token")

    def audit_links(self, parsed: dict[str, tuple[HttpResult, SimpleHTML]]) -> None:
        print("\n▶ Same-origin link audit")
        print("-" * 60)

        for area, (_, parser) in parsed.items():
            links = self.find_same_origin_links(parser)
            if not links:
                self.add("WARN", area, "link_inventory", "No same-origin links discovered")
                continue

            self.add("PASS", area, "link_inventory", f"{len(links)} same-origin link(s) discovered")

            for link in links[: self.args.max_links_per_surface]:
                url = link["url"]
                response = self.request("GET", url, timeout=20, cache=True)
                ok = 200 <= response.status < 400

                # Expected protected states.
                if "/platform/dashboard" in url and response.status == 403:
                    ok = True
                if "/ledger/export.csv" in url and response.status == 403 and "dashboard_locked" in area:
                    ok = True

                self.add(
                    "PASS" if ok else "FAIL",
                    area,
                    "same_origin_link",
                    f"{self.redact(link['href'])} -> {response.status}",
                    response.text[:700],
                )

    def audit_payment_and_ledger(self) -> None:
        print("\n▶ Payment + ledger contract audit")
        print("-" * 60)

        config = self.request("GET", f"/c/{self.campaign_slug}/payments/config")
        if self.expect_status("payments", "config_status", config, {200}):
            try:
                payload = json.loads(config.text)
                stripe = payload.get("stripe") or {}
                endpoints = payload.get("endpoints") or {}
                self.add("PASS" if stripe.get("enabled") else "WARN", "payments", "stripe_enabled", f"Stripe enabled={stripe.get('enabled')}")
                publishable = str(stripe.get("publishableKey") or "")
                self.add(
                    "PASS" if publishable.startswith(("pk_test_", "pk_live_")) else "FAIL",
                    "payments",
                    "stripe_publishable_key_shape",
                    "Stripe publishable key shape is valid" if publishable else "Stripe publishable key missing",
                )
                self.add(
                    "PASS" if endpoints.get("stripeCheckout") else "FAIL",
                    "payments",
                    "stripe_checkout_endpoint",
                    f"stripeCheckout={endpoints.get('stripeCheckout')}",
                )
            except Exception as error:
                self.add("FAIL", "payments", "config_json", f"Invalid config JSON: {error}", config.text[:900])

        missing = self.request("POST", f"/c/{self.campaign_slug}/checkout/session", json_data={})
        self.expect_status("payments", "checkout_rejects_missing_amount", missing, {400, 422})

        zero = self.request("POST", f"/c/{self.campaign_slug}/checkout/session", json_data={"amount": 0})
        self.expect_status("payments", "checkout_rejects_zero_amount", zero, {400, 422})

        if self.args.create_checkout:
            checkout = self.request(
                "POST",
                f"/c/{self.campaign_slug}/checkout/session",
                json_data={
                    "amount": 5,
                    "donor_name": "FutureFunded E2E QA",
                    "donor_email": f"futurefunded-e2e-{int(time.time())}@example.com",
                    "message": "E2E checkout session smoke.",
                },
                timeout=35,
            )
            if self.expect_status("payments", "checkout_session_create", checkout, {200}):
                try:
                    payload = json.loads(checkout.text)
                    has_session = bool(payload.get("id") or payload.get("url") or payload.get("clientSecret"))
                    self.add("PASS" if has_session else "FAIL", "payments", "checkout_session_payload", "Checkout session payload has session identifiers")
                except Exception as error:
                    self.add("FAIL", "payments", "checkout_session_json", f"Invalid checkout JSON: {error}", checkout.text[:900])
        else:
            self.add("WARN", "payments", "checkout_session_create", "Skipped. Pass --create-checkout to create a no-charge Stripe Checkout session.")

        ledger_summary_path = f"/c/{self.campaign_slug}/ledger/summary"
        ledger_events_path = f"/c/{self.campaign_slug}/ledger/events"
        export_path = f"/c/{self.campaign_slug}/ledger/export.csv"

        if self.operator_token:
            token_qs = urllib.parse.urlencode({"operator_token": self.operator_token})
            summary = self.request("GET", f"{ledger_summary_path}?{token_qs}")
            self.expect_status("ledger", "summary_status", summary, {200})

            events = self.request("GET", f"{ledger_events_path}?{token_qs}")
            self.expect_status("ledger", "events_status", events, {200})

            anonymous_export = self.request("GET", export_path)
            self.expect_status("ledger", "export_anonymous_protected", anonymous_export, {401, 403})

            export = self.request("GET", f"{export_path}?{token_qs}")
            if self.expect_status("ledger", "export_token_status", export, {200}):
                content_type_ok = "text/csv" in export.content_type.lower()
                self.add("PASS" if content_type_ok else "FAIL", "ledger", "export_content_type", f"Content-Type={export.content_type}")

                decoded = export.text.splitlines()
                header = decoded[0] if decoded else ""
                required_columns = {"record_type", "provider_session_id", "amount_cents", "status", "created_at"}
                columns = set(next(csv.reader([header])) if header else [])
                missing_columns = sorted(required_columns - columns)
                self.add(
                    "PASS" if not missing_columns else "FAIL",
                    "ledger",
                    "export_csv_header",
                    "CSV header has required columns" if not missing_columns else f"Missing columns: {missing_columns}",
                )
        else:
            self.add("WARN", "ledger", "operator_token", "No operator token available; protected ledger checks skipped")

    def audit_copy_quality(self, parsed: dict[str, tuple[HttpResult, SimpleHTML]]) -> None:
        print("\n▶ Copy quality audit")
        print("-" * 60)

        banned_fail = [
            "{{",
            "{%",
            "undefined",
            "null null",
            "lorem ipsum",
            "TODO",
            "FIXME",
        ]
        banned_warn = [
            "placeholder",
            "coming soon",
            "sample",
            "dummy",
        ]

        # "demo" may be intentionally present in protected/dashboard copy, so warn only.
        if self.args.strict_copy:
            banned_fail.append("demo")
        else:
            banned_warn.append("demo")

        for area, (_, parser) in parsed.items():
            text = parser.visible_text
            raw_attrs = " ".join(
                " ".join(
                    [tag]
                    + [
                        f"{key}={value}" if value else key
                        for key, value in attrs.items()
                    ]
                )
                for tag, attrs in parser.find_all()
            )
            haystack = f"{text} {raw_attrs}"

            for word in banned_fail:
                found = word.lower() in haystack.lower()
                self.add("FAIL" if found else "PASS", area, f"copy_no_{safe_code(word)}", f"{word!r} {'found' if found else 'not found'}")

            for word in banned_warn:
                found = word.lower() in haystack.lower()
                if found:
                    self.add("WARN", area, f"copy_warn_{safe_code(word)}", f"{word!r} found")
                else:
                    self.add("PASS", area, f"copy_warn_{safe_code(word)}", f"{word!r} not found")

    def run_subprocess_gate(self, label: str, command: list[str], timeout: int) -> None:
        print(f"\n▶ {label}")
        print("-" * 60)

        env = os.environ.copy()
        env["FF_AUDIT_BASE_URL"] = self.base_url
        if self.operator_token:
            env["FF_OPERATOR_ACCESS_TOKEN"] = self.operator_token

        try:
            completed = subprocess.run(
                command,
                cwd=Path.cwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
            output = completed.stdout or ""
            print(output[-5000:])
            self.add(
                "PASS" if completed.returncode == 0 else "FAIL",
                "subprocess",
                safe_code(label),
                f"{label} exit={completed.returncode}",
                output[-2000:],
            )
        except subprocess.TimeoutExpired as error:
            self.add("FAIL", "subprocess", safe_code(label), f"{label} timed out after {timeout}s", str(error))

    def write_reports(self) -> int:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        failures = [r for r in self.results if r.status == "FAIL"]
        warnings = [r for r in self.results if r.status == "WARN"]
        passes = [r for r in self.results if r.status == "PASS"]

        report = {
            "status": "FAIL" if failures else "PASS",
            "baseUrl": self.base_url,
            "campaignSlug": self.campaign_slug,
            "operatorTokenPresent": bool(self.operator_token),
            "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
            "counts": {
                "passes": len(passes),
                "warnings": len(warnings),
                "failures": len(failures),
                "total": len(self.results),
            },
            "results": [dataclasses.asdict(r) for r in self.results],
        }

        json_path = OUT_DIR / "e2e-product-audit.json"
        md_path = OUT_DIR / "e2e-product-audit.md"

        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        md = [
            "# FutureFunded E2E Product Audit",
            "",
            f"Status: **{report['status']}**",
            f"Base: `{self.redact(self.base_url)}`",
            f"Campaign: `{self.campaign_slug}`",
            f"Generated: `{report['generatedAt']}`",
            "",
            f"Passes: **{len(passes)}**",
            f"Warnings: **{len(warnings)}**",
            f"Failures: **{len(failures)}**",
            "",
            "| Status | Area | Code | Message |",
            "|---|---|---|---|",
        ]

        for r in self.results:
            md.append(
                f"| {r.status} | {r.area} | `{r.code}` | {r.message.replace('|', '\\|')} |"
            )

        md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

        print("\n" + "=" * 60)
        print(f"E2E PRODUCT AUDIT: {report['status']}")
        print(f"Report: {md_path}")
        print(f"JSON:   {json_path}")
        print("=" * 60)

        return 1 if failures else 0

    def run(self) -> int:
        print("\nFutureFunded E2E Product Audit")
        print("=" * 60)
        print(f"Base: {self.base_url}")
        print(f"Campaign: {self.campaign_slug}")
        print(f"Operator token: {'present' if self.operator_token else 'missing'}")
        print(f"Create checkout session: {self.args.create_checkout}")
        print("")

        parsed = self.audit_routes_and_html()
        self.audit_surface_contracts(parsed)
        self.audit_links(parsed)
        self.audit_payment_and_ledger()
        self.audit_copy_quality(parsed)

        if self.args.run_buttons:
            self.run_subprocess_gate("functional_button_contracts", ["scripts/dev/ffq", "buttons"], timeout=180)

        if self.args.run_visual:
            self.run_subprocess_gate("visual_surface_board", ["scripts/dev/ffq", "ui"], timeout=160)

        if self.args.run_money:
            self.run_subprocess_gate("money_loop_gate", ["scripts/dev/ffq", "money"], timeout=720)

        return self.write_reports()


def safe_code(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "check"


def read_operator_token() -> str:
    value = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if value:
        return value

    for path in TOKEN_FILES:
        try:
            value = path.read_text().strip()
            if value:
                return value
        except Exception:
            pass

    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FutureFunded comprehensive E2E product audit")
    parser.add_argument("--base-url", default=os.environ.get("FF_AUDIT_BASE_URL", DEFAULT_BASE_URL), help="Base URL to audit")
    parser.add_argument("--campaign", default=os.environ.get("FF_AUDIT_CAMPAIGN_SLUG", DEFAULT_CAMPAIGN), help="Campaign slug")
    parser.add_argument("--operator-token", default=read_operator_token(), help="Operator token. Prefer env/file; avoid printing.")
    parser.add_argument("--max-links-per-surface", type=int, default=32, help="Max same-origin links to check per surface")
    parser.add_argument("--create-checkout", action="store_true", help="Create a no-charge Stripe Checkout session smoke")
    parser.add_argument("--strict-copy", action="store_true", help="Treat 'demo' as copy failure instead of warning")
    parser.add_argument("--run-buttons", action="store_true", help="Run scripts/dev/ffq buttons inside this audit")
    parser.add_argument("--run-visual", action="store_true", help="Run scripts/dev/ffq ui inside this audit")
    parser.add_argument("--run-money", action="store_true", help="Run scripts/dev/ffq money inside this audit")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification for unusual staging environments")
    parser.add_argument("--verbose", action="store_true", help="Print detailed failure snippets")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    auditor = Auditor(
        base_url=args.base_url,
        campaign_slug=args.campaign,
        operator_token=args.operator_token,
        args=args,
    )

    try:
        return auditor.run()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

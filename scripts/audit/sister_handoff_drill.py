#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse, urlunparse, parse_qsl
from urllib.request import HTTPCookieProcessor, Request, build_opener
import http.cookiejar


DEFAULT_BASE_URL = "http://127.0.0.1:5000"
DEFAULT_EMAIL = "operator@getfuturefunded.com"
DEFAULT_PASSWORD = "ChangeMe123"
DEFAULT_CAMPAIGN_SLUG = "connect-atx-elite"


@dataclass
class DrillResult:
    step: str
    ok: bool
    status: int | None
    url: str
    detail: str


class HandoffDrillError(RuntimeError):
    pass


class HandoffClient:
    def __init__(self, base_url: str, timeout: int = 20):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.cookies = http.cookiejar.CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))

    def absolute_url(self, path_or_url: str) -> str:
        raw = str(path_or_url or "").strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        return urljoin(self.base_url, raw.lstrip("/"))

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        form: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int | None, str, str, dict[str, str]]:
        url = self.absolute_url(path_or_url)
        body: bytes | None = None
        final_headers: dict[str, str] = {}

        req_headers = {
            "User-Agent": "FutureFunded-Sister-Handoff-Drill/1.0",
            "Accept": "text/html,application/json,text/csv,*/*",
        }

        if headers:
            req_headers.update(headers)

        if json_payload is not None:
            body = json.dumps(json_payload).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
            req_headers["Accept"] = "application/json"

        elif form is not None:
            body = urlencode({k: "" if v is None else str(v) for k, v in form.items()}).encode("utf-8")
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = Request(url, data=body, headers=req_headers, method=method.upper())

        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8", errors="replace")
                final_headers = dict(response.headers.items())
                return response.status, payload, response.geturl(), final_headers
        except HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            final_headers = dict(exc.headers.items())
            return exc.code, payload, exc.geturl(), final_headers
        except URLError as exc:
            return None, str(exc), url, final_headers


def add_query(url: str, **params: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    for key, value in params.items():
        if value:
            query[key] = value

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query),
            parsed.fragment,
        )
    )


def extract_data_attr(source: str, attr: str) -> str:
    pattern = rf'{re.escape(attr)}=["\']([^"\']+)["\']'
    match = re.search(pattern, source)
    return html.unescape(match.group(1)) if match else ""


def extract_setup_ids(source: str) -> list[str]:
    ids = re.findall(r"setup_id=([a-f0-9]{16,64})", source, flags=re.I)
    seen: list[str] = []

    for item in ids:
        lowered = item.lower()
        if lowered not in seen:
            seen.append(lowered)

    return seen


def parse_json(payload: str) -> dict[str, Any]:
    try:
        data = json.loads(payload)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def status_label(status: str) -> str:
    return {
        "draft": "Draft",
        "review_needed": "Review Needed",
        "launch_ready": "Launch Ready",
        "launched": "Launched",
        "archived": "Archived",
    }.get(status, status.replace("_", " ").title())


class HandoffDrill:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.client = HandoffClient(args.base_url, timeout=args.timeout)
        self.results: list[DrillResult] = []
        self.operator_token = args.operator_token or ""
        self.created_setup_id = ""
        self.dashboard_html = ""

    def record(self, step: str, ok: bool, status: int | None, url: str, detail: str, *, critical: bool = False) -> None:
        self.results.append(DrillResult(step=step, ok=ok, status=status, url=url, detail=detail))
        icon = "✅" if ok else "❌"
        print(f"{icon} {step} — {detail}")

        if critical and not ok:
            raise HandoffDrillError(f"{step}: {detail}")

    def with_token(self, path_or_url: str) -> str:
        if not self.operator_token:
            return path_or_url

        absolute = self.client.absolute_url(path_or_url)
        return add_query(absolute, operator_token=self.operator_token)

    def get(self, path_or_url: str) -> tuple[int | None, str, str, dict[str, str]]:
        return self.client.request("GET", self.with_token(path_or_url))

    def post_json(self, path_or_url: str, payload: dict[str, Any]) -> tuple[int | None, str, str, dict[str, str]]:
        return self.client.request("POST", self.with_token(path_or_url), json_payload=payload)

    def post_form(self, path_or_url: str, payload: dict[str, Any]) -> tuple[int | None, str, str, dict[str, str]]:
        return self.client.request("POST", self.with_token(path_or_url), form=payload)

    def run(self) -> None:
        print("\n🚀 FutureFunded sister handoff drill")
        print(f"Base URL: {self.args.base_url}\n")

        self.step_login_page()
        self.step_login()
        self.step_dashboard()
        self.step_open_latest_setup()
        self.step_save_new_setup_version()
        self.step_status("review_needed")
        self.step_status("launch_ready")
        self.step_offline_support()
        self.step_export_csv()
        self.step_runbook_present()
        self.write_report()

        failed = [item for item in self.results if not item.ok]

        print("\n==============================")
        print("FutureFunded sister handoff result")
        print("==============================")
        print(f"Passed: {len(self.results) - len(failed)}")
        print(f"Failed: {len(failed)}")
        print(f"Output: {self.args.output_dir}")

        if failed:
            raise SystemExit(1)

        print("\n🎉 Sister handoff drill passed.")

    def step_login_page(self) -> None:
        status, body, url, _ = self.get("/platform/login?css_v=sister-handoff-drill")
        ok = status == 200 and "data-ff-login-root" in body and "data-ff-login-form" in body
        self.record(
            "Open login page",
            ok,
            status,
            url,
            "login page rendered with expected hooks" if ok else "login page missing expected hooks",
            critical=True,
        )

    def step_login(self) -> None:
        status, body, url, _ = self.client.request(
            "POST",
            "/platform/login",
            form={
                "email": self.args.email,
                "password": self.args.password,
                "next": "/platform/dashboard",
            },
        )

        ok = (
            status == 200
            and (
                "/platform/dashboard" in url
                or "data-ff-operator-root" in body
                or "Campaign setup records" in body
                or "Campaign operations" in body
            )
        )

        self.record(
            "Log in as operator",
            ok,
            status,
            url,
            "operator session created and dashboard reached" if ok else "operator login did not reach dashboard",
            critical=True,
        )

    def step_dashboard(self) -> None:
        status, body, url, _ = self.get("/platform/dashboard?css_v=sister-handoff-drill")
        self.dashboard_html = body

        checks = [
            "data-ff-operator-root",
            "Campaign setup records",
            "Recent donations",
            "Offline support",
            "Export CSV",
        ]

        missing = [item for item in checks if item not in body]
        ok = status == 200 and not missing

        self.record(
            "Open dashboard",
            ok,
            status,
            url,
            "dashboard contains setup records, donations, offline support, and export"
            if ok
            else f"dashboard missing: {', '.join(missing)}",
            critical=True,
        )

    def step_open_latest_setup(self) -> None:
        setup_ids = extract_setup_ids(self.dashboard_html)
        setup_id = setup_ids[0] if setup_ids else ""

        if not setup_id:
            self.record(
                "Open latest setup",
                False,
                None,
                self.client.absolute_url("/platform/dashboard"),
                "no setup_id found in dashboard",
                critical=True,
            )
            return

        status, body, url, _ = self.get(f"/platform/onboarding?setup_id={setup_id}&css_v=sister-handoff-drill")

        ok = status == 200 and (
            f'data-ff-loaded-setup-id="{setup_id}"' in body
            or "data-ff-onboarding-server-state" in body
            or setup_id in body
        )

        self.record(
            "Open latest setup",
            ok,
            status,
            url,
            f"loaded setup {setup_id[:10]}" if ok else f"could not load setup {setup_id}",
            critical=True,
        )

    def step_save_new_setup_version(self) -> None:
        stamp = int(time.time())

        payload = {
            "campaign_slug": self.args.campaign_slug,
            "organization_name": "Connect ATX Elite",
            "organization_type": "Youth team",
            "campaign_name": f"Connect ATX Elite Season Fund",
            "location": "Austin, TX",
            "goal": "$20000",
            "operator_email": self.args.email,
            "launch_window": "Before season launch",
            "primary_audience": "Families, alumni, local businesses",
            "support_story": "Travel, training, tournament fees, meals, equipment, and scholarship support.",
            "campaign_summary": f"Sister handoff drill setup version created at {stamp}.",
            "primary_sponsor_package": "Featured Sponsor · $1,500",
            "payment_stack": "Stripe and PayPal",
            "launch_notes": "Automated handoff drill: save setup version, update status, add offline support, export CSV.",
            "readiness_score": 94,
            "status": "draft",
            "source": "sister_handoff_drill",
        }

        status, body, url, _ = self.post_json("/platform/onboarding", payload)
        data = parse_json(body)
        setup_id = str(data.get("setup_id") or "")

        ok = status == 200 and data.get("ok") is True and bool(setup_id)
        if ok:
            self.created_setup_id = setup_id

        self.record(
            "Save new setup version",
            ok,
            status,
            url,
            f"created setup {setup_id[:10]}" if ok else data.get("message", "setup save failed"),
            critical=True,
        )

    def step_status(self, next_status: str) -> None:
        if not self.created_setup_id:
            self.record("Update setup status", False, None, "", "no created setup id available", critical=True)
            return

        status, body, url, _ = self.post_json(
            f"/platform/setup/{self.created_setup_id}/status",
            {"status": next_status},
        )
        data = parse_json(body)

        ok = status == 200 and data.get("ok") is True and data.get("status") == next_status

        self.record(
            f"Change status to {status_label(next_status)}",
            ok,
            status,
            url,
            data.get("message", f"status={data.get('status')}") if data else body[:180],
            critical=True,
        )

    def step_offline_support(self) -> None:
        status, body, url, _ = self.get("/platform/dashboard?css_v=sister-handoff-drill")
        offline_url = extract_data_attr(body, "data-ff-offline-url")

        if not offline_url:
            offline_url = f"/c/{self.args.campaign_slug}/ledger/offline-donation"

        payload = {
            "amount": "7.00",
            "donor_name": "Sister Handoff Test",
            "donor_email": "handoff-test@getfuturefunded.com",
            "internal_note": f"Automated sister handoff drill offline gift at {int(time.time())}.",
            "note": f"Automated sister handoff drill offline gift at {int(time.time())}.",
            "source": "sister_handoff_drill",
        }

        post_status, post_body, post_url, _ = self.post_json(offline_url, payload)
        data = parse_json(post_body)

        if not (post_status in {200, 201} and (data.get("ok", True) is not False)):
            post_status, post_body, post_url, _ = self.post_form(offline_url, payload)
            data = parse_json(post_body)

        ok = post_status in {200, 201} and (
            data.get("ok", True) is not False
            or "offline" in post_body.lower()
            or "donation" in post_body.lower()
        )

        self.record(
            "Add offline support entry",
            ok,
            post_status,
            post_url,
            data.get("message", "offline support accepted") if ok else post_body[:220],
            critical=True,
        )

    def step_export_csv(self) -> None:
        status, body, url, headers = self.get("/platform/dashboard?css_v=sister-handoff-drill")
        export_url = extract_data_attr(body, "data-ff-export-url")

        if not export_url:
            export_url = f"/c/{self.args.campaign_slug}/ledger/export.csv"

        csv_status, csv_body, csv_url, csv_headers = self.get(export_url)

        content_type = str(csv_headers.get("Content-Type") or csv_headers.get("content-type") or "")
        looks_like_csv = (
            "csv" in content_type.lower()
            or "amount" in csv_body.lower()
            or "donor" in csv_body.lower()
            or len(csv_body.strip().splitlines()) >= 1
        )

        ok = csv_status == 200 and looks_like_csv

        self.record(
            "Export CSV",
            ok,
            csv_status,
            csv_url,
            "CSV endpoint returned exportable content" if ok else "CSV endpoint did not return usable content",
            critical=True,
        )

    def step_runbook_present(self) -> None:
        required = [
            Path("docs/SISTER_DEMO_RUNBOOK.md"),
            Path("docs/PRODUCTION_HANDOFF_CHECKLIST.md"),
        ]

        missing = [str(path) for path in required if not path.exists()]
        ok = not missing

        self.record(
            "Confirm runbook/checklist",
            ok,
            None,
            "",
            "operator runbook and production checklist are present" if ok else f"missing: {', '.join(missing)}",
            critical=True,
        )

    def write_report(self) -> None:
        out_dir = Path(self.args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "base_url": self.args.base_url,
            "email": self.args.email,
            "campaign_slug": self.args.campaign_slug,
            "created_setup_id": self.created_setup_id,
            "results": [asdict(result) for result in self.results],
        }

        json_path = out_dir / "sister-handoff-drill-results.json"
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        lines = [
            "# FutureFunded Sister Handoff Drill",
            "",
            f"- Base URL: `{self.args.base_url}`",
            f"- Operator email: `{self.args.email}`",
            f"- Campaign slug: `{self.args.campaign_slug}`",
            f"- Created setup ID: `{self.created_setup_id or 'n/a'}`",
            "",
            "| Step | Result | Status | Detail |",
            "|---|---:|---:|---|",
        ]

        for result in self.results:
            mark = "✅ PASS" if result.ok else "❌ FAIL"
            status = "" if result.status is None else str(result.status)
            detail = result.detail.replace("|", "\\|")
            lines.append(f"| {result.step} | {mark} | {status} | {detail} |")

        md_path = out_dir / "sister-handoff-drill-results.md"
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        print(f"\n📝 Wrote {json_path}")
        print(f"📝 Wrote {md_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FutureFunded sister/operator handoff drill.")

    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--campaign-slug", default=DEFAULT_CAMPAIGN_SLUG)
    parser.add_argument("--operator-token", default="")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output-dir", default="docs/audits/sister-handoff")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        HandoffDrill(args).run()
    except HandoffDrillError as exc:
        print(f"\n❌ Handoff drill stopped: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

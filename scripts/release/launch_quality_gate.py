#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path.cwd()
LAUNCH_GATE_PROFILE = os.getenv("FF_LAUNCH_GATE_PROFILE", "release").strip().lower()
SKIP_SLOW_UI_GATES = LAUNCH_GATE_PROFILE in {"fast", "quick", "smoke"}
WEB_ROOT = ROOT / "apps/web"
STATIC_ROOT = WEB_ROOT / "app/static"
OUT_DIR = ROOT / "audit_outputs/launch-quality"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_PATH = ROOT / "docs/release-proof/launch-quality-baseline.json"

sys.path.insert(0, str(ROOT.resolve()))
sys.path.insert(0, str(WEB_ROOT.resolve()))

CSS_LINK_RE = re.compile(
    r"<link\b[^>]*\bhref=[\"']([^\"']+\.css(?:\?[^\"']*)?)[\"'][^>]*>",
    re.I,
)

SCRIPT_RE = re.compile(
    r"<script\b[^>]*\bsrc=[\"']([^\"']+\.js(?:\?[^\"']*)?)[\"'][^>]*>",
    re.I,
)

RETIRED_CSS_NAMES = {
    "platform-home.css",
    "login.css",
    "dashboard.css",
    "ff.homepage-flagship.css",
    "ff.campaign-polish.css",
    "ff.operator-dashboard.css",
    "ff.tokens.css",
    "ff.pages.css",
    "ff.base.css",
    "ff.checkout.css",
    "platform.bundle.css",
}

ROUTE_CONTRACTS: dict[str, dict[str, Any]] = {
    "/platform/": {
        "expected_css": ["apps/web/app/static/css/ff.css"],
        "must_any": [["FutureFunded", "ff-home", "data-ff-home-root", "ff-platformPage"]],
    },
    "/platform": {
        "expected_css": ["apps/web/app/static/css/ff.css"],
        "must_any": [["FutureFunded", "ff-home", "data-ff-home-root", "ff-platformPage"]],
    },
    "/c/connect-atx-elite": {
        "expected_css": [
            "apps/web/app/static/css/ff.css",
            "apps/web/app/static/css/campaign.css",
        ],
        "must_all": [
            "data-ff-page-root",
            "data-ff-open-checkout",
            "data-ff-donate-trigger",
            "data-ff-payment-trigger",
            "data-ff-open-sponsor",
            "data-ff-sponsor-modal",
            "data-ff-share",
            "ffCampaignConfig",
        ],
        "must_any": [
            ["data-ff-embedded-checkout-shell", "data-ff-checkout-sheet", "ff-embeddedCheckout", "ff-checkoutModal"],
            ["#give", "data-ff-donate-submit", "data-ff-amount-button"],
        ],
    },
    "/platform/login": {
        "expected_css": ["apps/web/app/static/css/ff.css"],
        "must_any": [["data-ff-login-root", "Sign in", "Login"]],
    },
    "/platform/dashboard": {
        "expected_css": ["apps/web/app/static/css/ff.css"],
        "allow_status": [200, 302, 401, 403],
        "must_any_if_200": [["data-ff-operator-root", "operator", "dashboard"]],
    },
}

PAYMENT_ROUTES = [
    "/c/connect-atx-elite/payments/config",
    "/c/connect-atx-elite/ledger/summary",
    "/c/connect-atx-elite/ledger/events",
]

EXPECTED_FILES = [
    "apps/web/app/static/css/ff.css",
    "apps/web/app/static/css/campaign.css",
    "apps/web/app/static/js/ff-campaign.js",
    "apps/web/app/templates/campaign/index.html",
    "apps/web/app/templates/platform/index.html",
    "apps/web/app/templates/platform/login.html",
    "apps/web/app/templates/platform/dashboard.html",
    "scripts/audit_active_frontend.py",
    "scripts/campaign-payment-smoke.mjs",
]


@dataclass
class Gate:
    checks: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def pass_check(self, name: str, details: Any = None) -> None:
        self.checks.append({"name": name, "status": "PASS", "details": details})

    def warn_check(self, name: str, message: str, details: Any = None) -> None:
        self.warnings.append(message)
        self.checks.append({"name": name, "status": "WARN", "message": message, "details": details})

    def fail_check(self, name: str, message: str, details: Any = None) -> None:
        self.errors.append(message)
        self.checks.append({"name": name, "status": "FAIL", "message": message, "details": details})


def run_cmd(cmd: list[str], *, timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or "") + f"\nTIMEOUT after {timeout}s"


def normalize_static_href(href: str) -> str | None:
    parsed = urlparse(href)
    path = unquote(parsed.path)
    if not path.startswith("/static/"):
        return None
    return str((STATIC_ROOT / path.replace("/static/", "", 1)).relative_to(ROOT))


def extract_static_files(html: str, regex: re.Pattern[str]) -> list[str]:
    out: list[str] = []
    for href in regex.findall(html):
        rel = normalize_static_href(href)
        if rel and rel not in out:
            out.append(rel)
    return out


def contains_any(html: str, options: list[str]) -> bool:
    return any(token in html for token in options)


def check_git(gate: Gate) -> None:
    code, out = run_cmd(["git", "status", "--short"])
    if code != 0:
        gate.fail_check("git status", "git status failed", out)
        return

    if out.strip():
        if os.getenv("FF_ALLOW_DIRTY_RELEASE") == "1":
            gate.warn_check("git clean", "working tree is dirty but FF_ALLOW_DIRTY_RELEASE=1", out.strip())
        else:
            gate.fail_check("git clean", "working tree is dirty", out.strip())
    else:
        gate.pass_check("git clean", "working tree clean")

    code, head = run_cmd(["git", "log", "--oneline", "-5"])
    if code == 0:
        gate.pass_check("git recent commits", head.strip())


def check_expected_files(gate: Gate) -> None:
    missing = [rel for rel in EXPECTED_FILES if not (ROOT / rel).exists()]
    if missing:
        gate.fail_check("expected files", "missing expected launch files", missing)
    else:
        gate.pass_check("expected files", EXPECTED_FILES)

    retired_existing = [
        f"apps/web/app/static/css/{name}"
        for name in RETIRED_CSS_NAMES
        if (ROOT / f"apps/web/app/static/css/{name}").exists()
    ]
    if retired_existing:
        gate.fail_check("retired page CSS removed", "retired page CSS still exists", retired_existing)
    else:
        gate.pass_check("retired page CSS removed")


def check_css_health(gate: Gate) -> None:
    files = {
        "ff.css": ROOT / "apps/web/app/static/css/ff.css",
        "campaign.css": ROOT / "apps/web/app/static/css/campaign.css",
    }

    for name, path in files.items():
        if not path.exists():
            gate.fail_check(f"{name} exists", f"{name} missing")
            continue

        text = path.read_text(errors="ignore")
        info = {
            "lines": len(text.splitlines()),
            "bytes": path.stat().st_size,
            "important": text.count("!important"),
        }

        if name == "ff.css":
            required = ["FutureFunded", "--ff-font-sans", ".ff-button", ".ff-card"]
        else:
            required = [".ff-campaignHero", ".ff-donatePanel", ".ff-shareDrawer", ".ff-sponsorModal", ".ff-checkoutModal"]

        missing = [token for token in required if token not in text]
        if missing:
            gate.fail_check(f"{name} tokens", f"{name} missing required tokens", {"missing": missing, **info})
        else:
            gate.pass_check(f"{name} tokens", info)

        if info["important"] > 1000:
            gate.warn_check(f"{name} important count", f"{name} has high !important count", info)


def load_app(gate: Gate):
    try:
        from app import create_app
        app = create_app()
        gate.pass_check("Flask app import", "create_app() loaded")
        return app
    except Exception as exc:
        gate.fail_check("Flask app import", f"create_app() failed: {exc}")
        return None


def check_db_bind(gate: Gate, app: Any) -> None:
    try:
        from apps.web.app.extensions import get_db_session

        with app.app_context():
            session = get_db_session()
            bind = session.get_bind()
            gate.pass_check("SQLAlchemy session bind", str(bind))
    except Exception as exc:
        gate.fail_check("SQLAlchemy session bind", f"session bind failed: {exc}")


def check_routes(gate: Gate, app: Any) -> None:
    with app.test_client() as client:
        for route, contract in ROUTE_CONTRACTS.items():
            response = client.get(route)
            html = response.get_data(as_text=True)
            css = extract_static_files(html, CSS_LINK_RE)
            js = extract_static_files(html, SCRIPT_RE)

            details = {
                "status": response.status_code,
                "css": css,
                "js": js,
                "html_bytes": len(html),
            }

            allowed = contract.get("allow_status", [200])
            if response.status_code not in allowed:
                gate.fail_check(f"{route} status", f"unexpected status {response.status_code}", details)
                continue

            expected_css = contract.get("expected_css")

            # Redirect/auth responses do not render the page shell, so they have no CSS stack.
            # Only enforce CSS authority when an HTML page actually renders.
            if 300 <= response.status_code < 400:
                gate.pass_check(
                    f"{route} CSS authority",
                    {"skipped": True, "reason": f"redirect status {response.status_code}", "css": css},
                )
            elif response.content_type.startswith("text/html"):
                if expected_css and css != expected_css:
                    gate.fail_check(
                        f"{route} CSS authority",
                        "CSS stack mismatch",
                        {"expected": expected_css, "actual": css, "status": response.status_code},
                    )
                else:
                    gate.pass_check(f"{route} CSS authority", css)

                retired = [
                    rel
                    for rel in css
                    if Path(rel).name in RETIRED_CSS_NAMES or "_quarantine" in rel or ".bak" in rel
                ]
                if retired:
                    gate.fail_check(f"{route} retired CSS", "route loads retired CSS", retired)
            else:
                gate.pass_check(
                    f"{route} CSS authority",
                    {"skipped": True, "reason": f"non-html content type {response.content_type}", "css": css},
                )

            for rel in css + js:
                if not (ROOT / rel).exists():
                    gate.fail_check(f"{route} static asset exists", f"missing static asset {rel}")

            if response.status_code == 200:
                for token in contract.get("must_all", []):
                    if token not in html:
                        gate.fail_check(f"{route} required token", f"missing token {token}")

                for group in contract.get("must_any", []):
                    if not contains_any(html, group):
                        gate.fail_check(f"{route} required token group", f"missing one of {group}")

                for group in contract.get("must_any_if_200", []):
                    if not contains_any(html, group):
                        gate.fail_check(f"{route} required 200 token group", f"missing one of {group}")

            gate.pass_check(f"{route} render", details)


def check_payment_routes(gate: Gate, app: Any) -> None:
    with app.test_client() as client:
        for route in PAYMENT_ROUTES:
            response = client.get(route)
            body = response.get_data(as_text=True)[:500]
            details = {
                "status": response.status_code,
                "content_type": response.content_type,
                "body_preview": body,
            }

            if response.status_code >= 500:
                gate.fail_check(f"{route} payment route", f"server error {response.status_code}", details)
            elif response.status_code in {200, 204, 301, 302, 401, 403, 404, 405}:
                gate.pass_check(f"{route} payment route", details)
            else:
                gate.warn_check(f"{route} payment route", f"unusual status {response.status_code}", details)


def check_template_static_refs(gate: Gate) -> None:
    bad: list[str] = []
    template_root = ROOT / "apps/web/app/templates"

    for template in template_root.rglob("*"):
        if not template.is_file():
            continue

        rel = str(template.relative_to(ROOT))

        # Ignore local/legacy backup templates. They are not part of the active render graph.
        if ".bak" in template.name or ".bak-" in rel or "/_quarantine/" in rel:
            continue

        if template.suffix not in {".html", ".jinja", ".j2"}:
            continue

        text = template.read_text(errors="ignore")

        css_refs = CSS_LINK_RE.findall(text)
        js_refs = SCRIPT_RE.findall(text)

        for href in css_refs:
            asset_name = Path(urlparse(href).path).name
            if asset_name in RETIRED_CSS_NAMES:
                bad.append(f"{rel}: active link tag references retired CSS {asset_name}")

            if "_quarantine" in href or ".bak" in href:
                bad.append(f"{rel}: active link tag references quarantine/backup asset {href}")

        for src in js_refs:
            if "_quarantine" in src or ".bak" in src:
                bad.append(f"{rel}: active script tag references quarantine/backup asset {src}")

    if bad:
        gate.fail_check("template retired asset references", "templates reference retired loaded assets", bad)
    else:
        gate.pass_check("template retired asset references")


def run_existing_audits(gate: Gate) -> None:
    code, out = run_cmd([sys.executable, "scripts/audit_active_frontend.py"], timeout=90)
    if code == 0 and "Errors:" in out and "none" in out:
        gate.pass_check("active frontend audit", out[-2500:])
    else:
        gate.fail_check("active frontend audit", "audit_active_frontend.py failed", out[-5000:])

    if (ROOT / "scripts/campaign-payment-smoke.mjs").exists():
        env = os.environ.copy()
        env.setdefault("FF_BASE_URL", "http://127.0.0.1:5000")
        proc = subprocess.run(
            ["node", "scripts/campaign-payment-smoke.mjs"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
            env=env,
        )
        if proc.returncode == 0 and "FutureFunded campaign smoke: PASS" in proc.stdout:
            gate.pass_check("campaign payment smoke", proc.stdout[-2500:])
        else:
            gate.fail_check("campaign payment smoke", "campaign smoke failed", proc.stdout[-5000:])


def write_report(gate: Gate) -> None:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report = {
        "ok": not gate.errors,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "errors": gate.errors,
        "warnings": gate.warnings,
        "checks": gate.checks,
    }

    latest_json = OUT_DIR / "latest.json"
    latest_md = OUT_DIR / "latest.md"
    stamped_json = OUT_DIR / f"launch-quality-{stamp}.json"
    stamped_md = OUT_DIR / f"launch-quality-{stamp}.md"

    latest_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    stamped_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# FutureFunded Launch Quality Gate",
        "",
        f"**Status:** {'PASS ✅' if report['ok'] else 'FAIL ❌'}",
        f"**Checked:** {report['checked_at']}",
        "",
        "## Summary",
        "",
        f"- Checks: {len(gate.checks)}",
        f"- Errors: {len(gate.errors)}",
        f"- Warnings: {len(gate.warnings)}",
        "",
        "## Errors",
        "",
    ]

    lines.extend([f"- {x}" for x in gate.errors] or ["- None"])

    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {x}" for x in gate.warnings] or ["- None"])

    lines.extend(["", "## Checks", ""])
    for check in gate.checks:
        status = check["status"]
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(status, "•")
        lines.append(f"- {icon} **{check['name']}**")

    latest_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    stamped_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(latest_md.read_text(encoding="utf-8"))
    print(f"\nJSON: {latest_json}")
    print(f"Markdown: {latest_md}")


def main() -> int:
    gate = Gate()

    check_git(gate)
    check_expected_files(gate)
    check_css_health(gate)
    check_template_static_refs(gate)

    app = load_app(gate)
    if app is not None:
        check_db_bind(gate, app)
        check_routes(gate, app)
        check_payment_routes(gate, app)

    run_existing_audits(gate)

    if (ROOT / "scripts/release/payment_readiness_gate.py").exists():
        proc = subprocess.run(
            [sys.executable, "scripts/release/payment_readiness_gate.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
        )

        if proc.returncode == 0 and "Status:** PASS" in proc.stdout:
            gate.pass_check("payment readiness gate", proc.stdout[-2500:])
        else:
            gate.fail_check("payment readiness gate", "payment readiness failed", proc.stdout[-5000:])

    if SKIP_SLOW_UI_GATES:
        gate.pass_check("console hygiene gate skipped", {"profile": LAUNCH_GATE_PROFILE})
    elif (ROOT / "scripts/release/console_hygiene_gate.mjs").exists():
        env = os.environ.copy()
        env.setdefault("FF_BASE_URL", "http://127.0.0.1:5000")
        proc = subprocess.run(
            ["node", "scripts/release/console_hygiene_gate.mjs"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
            check=False,
            env=env,
        )

        if proc.returncode == 0 and "Status:** PASS" in proc.stdout:
            gate.pass_check("console hygiene gate", proc.stdout[-2500:])
        else:
            gate.fail_check("console hygiene gate", "console hygiene failed", proc.stdout[-5000:])

    if SKIP_SLOW_UI_GATES:
        gate.pass_check("performance budget gate skipped", {"profile": LAUNCH_GATE_PROFILE})
    elif (ROOT / "scripts/release/performance_budget_gate.mjs").exists():
        env = os.environ.copy()
        env.setdefault("FF_BASE_URL", "http://127.0.0.1:5000")
        proc = subprocess.run(
            ["node", "scripts/release/performance_budget_gate.mjs"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
            check=False,
            env=env,
        )

        if proc.returncode == 0 and "Status:** PASS" in proc.stdout:
            gate.pass_check("performance budget gate", proc.stdout[-2500:])
        else:
            gate.fail_check("performance budget gate", "performance budget failed", proc.stdout[-5000:])

    if (ROOT / "scripts/release/accessibility_gate.mjs").exists():
        env = os.environ.copy()
        env.setdefault("FF_BASE_URL", "http://127.0.0.1:5000")
        proc = subprocess.run(
            ["node", "scripts/release/accessibility_gate.mjs"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
            check=False,
            env=env,
        )

        if proc.returncode == 0 and "Status:** PASS" in proc.stdout:
            gate.pass_check("accessibility gate", proc.stdout[-2500:])
        else:
            gate.fail_check("accessibility gate", "accessibility failed", proc.stdout[-5000:])

    if SKIP_SLOW_UI_GATES:
        gate.pass_check("page beauty gate skipped", {"profile": LAUNCH_GATE_PROFILE})
    else:
        if (ROOT / "scripts/release/page_beauty_gate.mjs").exists():
            env = os.environ.copy()
            env.setdefault("FF_BASE_URL", "http://127.0.0.1:5000")
            proc = subprocess.run(
                ["node", "scripts/release/page_beauty_gate.mjs"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=180,
                check=False,
                env=env,
            )

            if proc.returncode == 0 and "Status:** PASS" in proc.stdout:
                gate.pass_check("page beauty gate", proc.stdout[-2500:])
            else:
                gate.fail_check("page beauty gate", "page beauty failed", proc.stdout[-5000:])


    if SKIP_SLOW_UI_GATES:
        gate.pass_check("visual screenshot ratchet skipped", {"profile": LAUNCH_GATE_PROFILE})
    else:
        if (ROOT / "scripts/release/visual_ratchet_gate.mjs").exists():
            env = os.environ.copy()
            env.setdefault("FF_BASE_URL", "http://127.0.0.1:5000")
            proc = subprocess.run(
                ["node", "scripts/release/visual_ratchet_gate.mjs"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=180,
                check=False,
                env=env,
            )

            if proc.returncode == 0 and "Status:** PASS" in proc.stdout:
                gate.pass_check("visual screenshot ratchet", proc.stdout[-2500:])
            else:
                gate.fail_check("visual screenshot ratchet", "visual ratchet failed", proc.stdout[-5000:])


    write_report(gate)

    return 1 if gate.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

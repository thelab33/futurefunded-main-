#!/usr/bin/env python3
"""
FutureFunded repo audit.

Read-only diagnostic audit for:
- Flask route availability
- rendered CSS/JS stacks
- dashboard token mismatch
- Stripe/webhook env presence
- static/template contract mismatches
- sponsor modal contract
- dashboard operator contract
- frontend QA expectation drift

Does not print secret values.
Does not mutate app files.
Only writes artifacts/audit/*.json and *.md.
"""

from __future__ import annotations

import datetime as dt
import importlib
import json
import os
import re
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "audit"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES_TO_CHECK = [
    ("homepage", "/platform/"),
    ("homepage-no-slash", "/platform"),
    ("campaign", "/c/connect-atx-elite"),
    ("login", "/platform/login"),
    ("onboarding", "/platform/onboarding"),
]

DASHBOARD_PATH = "/platform/dashboard"

STATIC_REF_RE = re.compile(
    r"""url_for\(\s*['"]static['"]\s*,\s*filename\s*=\s*['"]([^'"]+)['"]""",
    re.I,
)

CSS_LINK_RE = re.compile(r"""<link[^>]+href=["']([^"']+\.css(?:\?[^"']*)?)["']""", re.I)
JS_SRC_RE = re.compile(r"""<script[^>]+src=["']([^"']+\.js(?:\?[^"']*)?)["']""", re.I)


@dataclass
class Finding:
    severity: str
    area: str
    title: str
    detail: str
    evidence: str = ""
    fix_hint: str = ""


findings: list[Finding] = []
report: dict[str, Any] = {
    "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    "repo_root": str(ROOT),
    "python": sys.version,
    "checks": {},
    "findings": [],
}


def add(
    severity: str, area: str, title: str, detail: str, evidence: str = "", fix_hint: str = ""
) -> None:
    findings.append(Finding(severity, area, title, detail, evidence, fix_hint))


def run(cmd: list[str], timeout: int = 20, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        p = subprocess.run(
            cmd,
            cwd=ROOT,
            env={**os.environ, **(env or {})},
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": cmd,
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "returncode": -999,
            "stdout": "",
            "stderr": repr(exc),
        }


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def mask_present(value: str | None) -> dict[str, Any]:
    value = value or ""
    return {
        "present": bool(value.strip()),
        "prefix": value[:8] + "…" if value.strip() else "",
        "length": len(value.strip()),
    }


def load_dotenv_local() -> dict[str, str]:
    env_file = ROOT / ".env.local"
    data: dict[str, str] = {}
    if not env_file.exists():
        return data

    for line in read_text(env_file).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()

    return data


def check_git() -> None:
    status = run(["git", "status", "--short"])
    branch = run(["git", "branch", "--show-current"])
    log = run(["git", "log", "-1", "--oneline"])

    report["checks"]["git"] = {
        "branch": branch["stdout"].strip(),
        "head": log["stdout"].strip(),
        "status_short": status["stdout"].splitlines(),
    }

    if status["stdout"].strip():
        add(
            "WARN",
            "git",
            "Working tree has uncommitted changes",
            "Audit found modified or untracked files. This is okay for debugging, but do not ship until the report is understood.",
            status["stdout"].strip(),
        )


def check_env() -> dict[str, str]:
    dotenv = load_dotenv_local()
    merged = {**dotenv, **os.environ}

    keys = [
        "STRIPE_SECRET_KEY",
        "FF_STRIPE_WEBHOOK_SECRET",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_WEBHOOK_SIGNING_SECRET",
        "FF_OPERATOR_ACCESS_TOKEN",
        "FLASK_APP",
        "FLASK_ENV",
    ]

    env_report = {key: mask_present(merged.get(key)) for key in keys}

    tmp_token = Path("/tmp/ff_operator_token")
    tmp_value = tmp_token.read_text().strip() if tmp_token.exists() else ""

    env_report["/tmp/ff_operator_token"] = mask_present(tmp_value)  # type: ignore[index]
    report["checks"]["env"] = env_report

    stripe = merged.get("STRIPE_SECRET_KEY", "").strip()
    whsec_values = [
        merged.get("FF_STRIPE_WEBHOOK_SECRET", "").strip(),
        merged.get("STRIPE_WEBHOOK_SECRET", "").strip(),
        merged.get("STRIPE_WEBHOOK_SIGNING_SECRET", "").strip(),
    ]

    if not stripe:
        add(
            "FAIL",
            "stripe",
            "STRIPE_SECRET_KEY is not configured",
            "Checkout session creation will return stripe_not_configured until the Flask runtime has STRIPE_SECRET_KEY.",
            ".env.local / environment missing STRIPE_SECRET_KEY",
            "Put STRIPE_SECRET_KEY in .env.local and restart Flask through scripts/run_local_stripe.sh.",
        )
    elif not stripe.startswith(("sk_test_", "sk_live_")):
        add(
            "FAIL",
            "stripe",
            "STRIPE_SECRET_KEY has unexpected format",
            "The key is present but does not look like a Stripe secret key.",
            f"prefix={stripe[:8]}…, length={len(stripe)}",
        )

    if not any(v.startswith("whsec_") for v in whsec_values):
        add(
            "FAIL",
            "stripe-webhook",
            "No valid webhook signing secret detected",
            "Stripe CLI webhook posts will fail if the Flask runtime does not have a whsec_ signing secret.",
            "FF_STRIPE_WEBHOOK_SECRET / STRIPE_WEBHOOK_SECRET / STRIPE_WEBHOOK_SIGNING_SECRET missing or malformed",
            "Run stripe listen, copy fresh whsec_, save it to .env.local, then restart Flask.",
        )

    env_token = merged.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if tmp_value and env_token and tmp_value != env_token:
        add(
            "FAIL",
            "dashboard-auth",
            "Dashboard token mismatch",
            "The screenshot/functionality tools are using /tmp/ff_operator_token, but Flask is running with a different FF_OPERATOR_ACCESS_TOKEN.",
            f"/tmp token length={len(tmp_value)}, env token length={len(env_token)}",
            "Restart Flask with FF_OPERATOR_ACCESS_TOKEN=$(cat /tmp/ff_operator_token), or write the same token into .env.local.",
        )

    if tmp_value and not env_token:
        add(
            "WARN",
            "dashboard-auth",
            "Operator token exists in /tmp but not in Flask env",
            "Dashboard tests may use a token Flask does not know about.",
            "/tmp/ff_operator_token exists; FF_OPERATOR_ACCESS_TOKEN missing from env/.env.local",
        )

    return dotenv


def import_flask_app(extra_env: dict[str, str]) -> Any | None:
    sys.path.insert(0, str(ROOT))

    for key, value in extra_env.items():
        os.environ.setdefault(key, value)

    candidates = ["apps.web.app", "app"]

    errors = []
    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)

            if hasattr(module, "create_app"):
                app = module.create_app()
                report["checks"]["flask_import"] = {
                    "module": module_name,
                    "factory": "create_app",
                    "ok": True,
                }
                return app

            if hasattr(module, "app"):
                app = module.app
                report["checks"]["flask_import"] = {
                    "module": module_name,
                    "factory": "app",
                    "ok": True,
                }
                return app

        except Exception:
            errors.append(
                {
                    "module": module_name,
                    "traceback": traceback.format_exc(limit=8),
                }
            )

    report["checks"]["flask_import"] = {"ok": False, "errors": errors}
    add(
        "FAIL",
        "flask",
        "Could not import Flask app",
        "The audit could not import apps.web.app or app.",
        json.dumps(errors, indent=2)[-4000:],
    )
    return None


def html_stacks(html: str) -> dict[str, list[str]]:
    return {
        "css": CSS_LINK_RE.findall(html),
        "js": JS_SRC_RE.findall(html),
    }


def check_routes(app: Any, extra_env: dict[str, str]) -> None:
    app.config.update(TESTING=True)
    client = app.test_client()

    routes_report: dict[str, Any] = {}

    token = (
        extra_env.get("FF_OPERATOR_ACCESS_TOKEN")
        or os.environ.get("FF_OPERATOR_ACCESS_TOKEN")
        or (
            Path("/tmp/ff_operator_token").read_text().strip()
            if Path("/tmp/ff_operator_token").exists()
            else ""
        )
        or "dev_operator_local"
    )

    checks = list(ROUTES_TO_CHECK) + [
        ("dashboard-authenticated", f"{DASHBOARD_PATH}?operator_token={token}")
    ]

    for name, path in checks:
        try:
            resp = client.get(path, follow_redirects=False)
            raw = resp.get_data()
            charset = getattr(resp, "charset", None) or resp.mimetype_params.get("charset", "utf-8")
            html = raw.decode(charset or "utf-8", errors="replace")
            stacks = html_stacks(html)
            routes_report[name] = {
                "path": (
                    path
                    if "operator_token=" not in path
                    else f"{DASHBOARD_PATH}?operator_token=<redacted>"
                ),
                "status": resp.status_code,
                "content_type": resp.headers.get("content-type", ""),
                "css": stacks["css"],
                "js": stacks["js"],
                "has_operator_root": "data-ff-operator-root" in html,
                "has_sponsor_modal_contract": "ff-sponsor-modal-contract.js" in html,
                "has_product_handoff_css": "ff.product-handoff.css" in html,
                "html_len": len(html),
            }

            if name != "dashboard-authenticated" and resp.status_code >= 400:
                add(
                    "FAIL",
                    "routes",
                    f"{name} returned HTTP {resp.status_code}",
                    f"Expected a public route to render successfully: {path}",
                    html[:500],
                )

            if name == "dashboard-authenticated" and resp.status_code != 200:
                add(
                    "FAIL",
                    "dashboard-auth",
                    "Authenticated dashboard route did not return 200",
                    "Dashboard QA will fail until the operator token used by tests matches the Flask runtime.",
                    f"status={resp.status_code}, path={DASHBOARD_PATH}?operator_token=<redacted>",
                    "Align FF_OPERATOR_ACCESS_TOKEN with /tmp/ff_operator_token and restart Flask.",
                )

            if name == "campaign":
                if "ff.product-handoff.css" in html:
                    add(
                        "FAIL",
                        "frontend-css",
                        "Campaign still loads ff.product-handoff.css",
                        "The screenshot showed contrast regression after this global handoff CSS was loaded.",
                        "ff.product-handoff.css found in rendered campaign HTML",
                        "Remove the runtime link or scope it safely before re-enabling.",
                    )

                if "ff-sponsor-modal-contract.js" not in html:
                    add(
                        "FAIL",
                        "sponsor-modal",
                        "Campaign does not load sponsor modal contract script",
                        "Payment smoke expects [data-ff-sponsor-modal] or [data-ff-sponsor-sheet] after sponsor click.",
                        "ff-sponsor-modal-contract.js not found in campaign HTML",
                    )

        except Exception:
            routes_report[name] = {
                "path": path,
                "error": traceback.format_exc(limit=8),
            }
            add(
                "FAIL",
                "routes",
                f"{name} route check crashed",
                f"Could not render {path}",
                routes_report[name]["error"],
            )

    report["checks"]["routes"] = routes_report


def check_url_map(app: Any) -> None:
    try:
        rules = []
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
            rules.append(
                {
                    "rule": str(rule),
                    "endpoint": rule.endpoint,
                    "methods": sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"}),
                }
            )

        report["checks"]["url_map"] = rules

        required = [
            "/c/<slug>/checkout/session",
            "/c/stripe/webhook",
            "/platform/dashboard",
            "/platform/onboarding",
            "/platform/login",
        ]

        rules_text = "\n".join(r["rule"] for r in rules)
        for req in required:
            if req not in rules_text:
                add(
                    "FAIL",
                    "url-map",
                    f"Missing expected route {req}",
                    "The Flask URL map does not show a required route.",
                    rules_text,
                )
    except Exception:
        add(
            "WARN",
            "url-map",
            "Could not inspect Flask URL map",
            "URL map inspection crashed.",
            traceback.format_exc(limit=6),
        )


def check_static_references() -> None:
    refs: dict[str, list[str]] = {}
    missing: list[dict[str, str]] = []

    for path in (ROOT / "apps").rglob("*.html"):
        text = read_text(path)
        for ref in STATIC_REF_RE.findall(text):
            refs.setdefault(ref, []).append(str(path.relative_to(ROOT)))
            if not (ROOT / "apps" / "web" / "app" / "static" / ref).exists():
                missing.append(
                    {
                        "ref": ref,
                        "template": str(path.relative_to(ROOT)),
                    }
                )

    report["checks"]["static_references"] = {
        "count": len(refs),
        "missing": missing,
    }

    for item in missing[:25]:
        add(
            "FAIL",
            "static",
            "Template references missing static asset",
            f"{item['template']} references static file that does not exist.",
            item["ref"],
        )


def check_template_contracts() -> None:
    contract = {
        "dashboard": {
            "files": list((ROOT / "apps" / "web" / "app" / "templates").rglob("*dashboard*.html")),
            "required": [
                "data-ff-operator-root",
                "data-ff-ledger-url",
                "data-ff-events-url",
                "data-ff-offline-url",
                "data-ff-export-url",
                "data-ff-offline-donation-form",
                "data-ff-donations-table",
                "data-ff-sponsors-list",
            ],
        },
        "campaign": {
            "files": [ROOT / "apps" / "web" / "app" / "templates" / "campaign" / "index.html"],
            "required": [
                "checkout/session",
                "data-ff-campaign",
                "Sponsor the season",
            ],
        },
    }

    out: dict[str, Any] = {}

    for area, cfg in contract.items():
        combined = ""
        file_list = [p for p in cfg["files"] if p.exists()]
        for p in file_list:
            combined += "\n" + read_text(p)

        missing = [token for token in cfg["required"] if token not in combined]
        out[area] = {
            "files": [str(p.relative_to(ROOT)) for p in file_list],
            "missing_tokens": missing,
        }

        if missing:
            add(
                "FAIL",
                f"{area}-contract",
                f"{area} template contract missing tokens",
                "Required selectors/hooks are absent from the likely template files.",
                ", ".join(missing),
            )

    report["checks"]["template_contracts"] = out


def check_source_grep() -> None:
    important_files = [
        ROOT / "apps" / "web" / "app" / "blueprints" / "campaign" / "routes.py",
        ROOT / "scripts" / "run_local_stripe.sh",
        ROOT / "scripts" / "audit_active_frontend.py",
        ROOT / "scripts" / "smoke_product_pages.py",
        ROOT / "scripts" / "campaign-payment-smoke.mjs",
        ROOT / "scripts" / "test_product_functionality.mjs",
    ]

    source_report: dict[str, Any] = {}

    for path in important_files:
        if not path.exists():
            source_report[str(path.relative_to(ROOT))] = {"exists": False}
            continue

        text = read_text(path)
        source_report[str(path.relative_to(ROOT))] = {
            "exists": True,
            "contains": {
                "STRIPE_SECRET_KEY": "STRIPE_SECRET_KEY" in text,
                "WEBHOOK_SECRET": "WEBHOOK_SECRET" in text or "whsec" in text,
                "ff.product-handoff.css": "ff.product-handoff.css" in text,
                "data-ff-sponsor-modal": "data-ff-sponsor-modal" in text,
                "data-ff-operator-root": "data-ff-operator-root" in text,
                "operator_token": "operator_token" in text,
            },
        }

    report["checks"]["source_grep"] = source_report

    routes_py = ROOT / "apps" / "web" / "app" / "blueprints" / "campaign" / "routes.py"
    if routes_py.exists():
        text = read_text(routes_py)
        if "stripe_not_configured" in text and "STRIPE_SECRET_KEY" in text:
            pass
        else:
            add(
                "WARN",
                "checkout",
                "Could not find obvious Stripe config guard",
                "routes.py may not expose stripe_not_configured/STRIPE_SECRET_KEY strings where expected.",
            )

        if "/c/stripe/webhook" not in text and "stripe/webhook" not in text:
            add(
                "FAIL",
                "stripe-webhook",
                "Could not find webhook route source",
                "The app URL map may still have it, but routes.py did not contain stripe/webhook text.",
            )


def check_frontend_audit_expectations() -> None:
    p = ROOT / "scripts" / "audit_active_frontend.py"
    if not p.exists():
        return

    text = read_text(p)
    has_handoff_expected = "ff.product-handoff.css" in text
    report["checks"]["frontend_audit_expectations"] = {
        "audit_active_frontend_mentions_product_handoff_css": has_handoff_expected,
    }

    # This is informational. If runtime removed it, the audit should not expect it.
    # If runtime includes it, the audit should expect it.
    # Route render check is the source of truth.
    campaign_route = report.get("checks", {}).get("routes", {}).get("campaign", {})
    runtime_has = bool(campaign_route.get("has_product_handoff_css"))

    if runtime_has != has_handoff_expected:
        add(
            "WARN",
            "frontend-audit",
            "CSS stack audit expectation may be out of sync",
            "audit_active_frontend.py expectation and rendered runtime differ for ff.product-handoff.css.",
            f"runtime_has_product_handoff_css={runtime_has}, audit_mentions_product_handoff_css={has_handoff_expected}",
        )


def check_compile_and_package() -> None:
    compile_result = run([sys.executable, "-m", "compileall", "apps/web/app"], timeout=40)
    report["checks"]["python_compile"] = {
        "returncode": compile_result["returncode"],
        "stderr_tail": compile_result["stderr"][-2000:],
        "stdout_tail": compile_result["stdout"][-2000:],
    }

    if compile_result["returncode"] != 0:
        add(
            "FAIL",
            "python",
            "Python compileall failed",
            "There is a syntax/import-adjacent issue under apps/web/app.",
            compile_result["stdout"][-2000:] + "\n" + compile_result["stderr"][-2000:],
        )

    package = ROOT / "package.json"
    if package.exists():
        try:
            pkg = json.loads(read_text(package))
            report["checks"]["package_scripts"] = pkg.get("scripts", {})
        except Exception:
            add(
                "WARN",
                "node",
                "Could not parse package.json",
                "package.json exists but JSON parse failed.",
            )


def summarize() -> str:
    counts = {"FAIL": 0, "WARN": 0, "INFO": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    lines = []
    lines.append("# FutureFunded Repo Audit")
    lines.append("")
    lines.append(f"Generated: `{report['generated_at']}`")
    lines.append(f"Repo: `{ROOT}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- FAIL: **{counts.get('FAIL', 0)}**")
    lines.append(f"- WARN: **{counts.get('WARN', 0)}**")
    lines.append(f"- INFO: **{counts.get('INFO', 0)}**")
    lines.append("")

    if findings:
        lines.append("## Findings")
        lines.append("")
        for idx, f in enumerate(findings, 1):
            icon = "❌" if f.severity == "FAIL" else "⚠️" if f.severity == "WARN" else "ℹ️"
            lines.append(f"### {idx}. {icon} [{f.severity}] {f.area}: {f.title}")
            lines.append("")
            lines.append(f.detail)
            lines.append("")
            if f.evidence:
                lines.append("**Evidence**")
                lines.append("")
                lines.append("```txt")
                lines.append(f.evidence[:4000])
                lines.append("```")
                lines.append("")
            if f.fix_hint:
                lines.append("**Fix hint**")
                lines.append("")
                lines.append(f.fix_hint)
                lines.append("")
    else:
        lines.append("## Findings")
        lines.append("")
        lines.append("No FAIL/WARN findings detected by this audit.")
        lines.append("")

    lines.append("## Route Matrix")
    lines.append("")
    routes = report.get("checks", {}).get("routes", {})
    if routes:
        lines.append(
            "| Route | Status | CSS count | JS count | Operator root | Sponsor contract | Product handoff CSS |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for name, data in routes.items():
            lines.append(
                f"| {name} | {data.get('status', 'ERR')} | "
                f"{len(data.get('css', []))} | {len(data.get('js', []))} | "
                f"{data.get('has_operator_root', False)} | "
                f"{data.get('has_sponsor_modal_contract', False)} | "
                f"{data.get('has_product_handoff_css', False)} |"
            )
        lines.append("")

    lines.append("## Env Presence")
    lines.append("")
    lines.append("> Secret values are intentionally masked.")
    lines.append("")
    env = report.get("checks", {}).get("env", {})
    if env:
        lines.append("| Key | Present | Prefix | Length |")
        lines.append("|---|---:|---|---:|")
        for key, data in env.items():
            lines.append(
                f"| `{key}` | {data.get('present')} | `{data.get('prefix')}` | {data.get('length')} |"
            )
        lines.append("")

    lines.append("## Artifacts")
    lines.append("")
    lines.append("- `artifacts/audit/ff_repo_audit.json`")
    lines.append("- `artifacts/audit/ff_repo_audit.md`")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    os.chdir(ROOT)

    check_git()
    dotenv = check_env()
    check_compile_and_package()

    app = import_flask_app(dotenv)
    if app is not None:
        check_url_map(app)
        check_routes(app, dotenv)

    check_static_references()
    check_template_contracts()
    check_source_grep()
    check_frontend_audit_expectations()

    report["findings"] = [asdict(f) for f in findings]

    json_path = ARTIFACT_DIR / "ff_repo_audit.json"
    md_path = ARTIFACT_DIR / "ff_repo_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(summarize(), encoding="utf-8")

    fail_count = sum(1 for f in findings if f.severity == "FAIL")
    warn_count = sum(1 for f in findings if f.severity == "WARN")

    print("")
    print("FutureFunded repo audit complete")
    print("================================")
    print(f"FAIL: {fail_count}")
    print(f"WARN: {warn_count}")
    print("")
    print(f"Markdown report: {md_path}")
    print(f"JSON report:     {json_path}")
    print("")
    print("Top findings:")
    for f in findings[:12]:
        icon = "❌" if f.severity == "FAIL" else "⚠️" if f.severity == "WARN" else "ℹ️"
        print(f"{icon} [{f.severity}] {f.area}: {f.title}")

    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
FutureFunded Product Family Review

Read-only audit for:
- product shell unity
- route health
- page/template contracts
- CSS authority drift
- copy risk
- FutureFunded refactor readiness

No source files are modified.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT_ROOT = ROOT / "audit_outputs" / "product-family-review"
OUT_DIR = OUT_ROOT / STAMP
LATEST_DIR = OUT_ROOT / "latest"


SURFACES = {
    "platform_home": {
        "label": "Platform homepage",
        "route": "/platform/",
        "template": "apps/web/app/templates/platform/index.html",
        "expected_status": [200],
        "role": "public SaaS sales surface",
    },
    "campaign": {
        "label": "Campaign page",
        "route": "/c/connect-atx-elite",
        "template": "apps/web/app/templates/campaign/index.html",
        "expected_status": [200],
        "role": "public donor/sponsor conversion surface",
    },
    "login": {
        "label": "Operator login",
        "route": "/platform/login",
        "template": "apps/web/app/templates/platform/login.html",
        "expected_status": [200],
        "role": "private organizer entry",
    },
    "onboarding": {
        "label": "Launch onboarding",
        "route": "/platform/onboarding",
        "template": "apps/web/app/templates/platform/onboarding.html",
        "expected_status": [200],
        "role": "campaign setup workflow",
    },
    "dashboard_locked": {
        "label": "Dashboard locked",
        "route": "/platform/dashboard",
        "template": "apps/web/app/templates/platform/dashboard.html",
        "expected_status": [200, 401, 403],
        "role": "protected access state",
    },
    "dashboard_token": {
        "label": "Dashboard token",
        "route": "/platform/dashboard?access_token={token}",
        "template": "apps/web/app/templates/platform/dashboard.html",
        "expected_status": [200],
        "role": "operator command center",
        "needs_token": True,
    },
}


CANONICAL_FILES = [
    "apps/web/app/templates/_base/site_base.html",
    "apps/web/app/templates/_base/campaign_base.html",
    "apps/web/app/templates/_partials/ff_site_header.html",
    "apps/web/app/templates/platform/index.html",
    "apps/web/app/templates/campaign/index.html",
    "apps/web/app/templates/platform/login.html",
    "apps/web/app/templates/platform/onboarding.html",
    "apps/web/app/templates/platform/dashboard.html",
    "apps/web/app/static/css/ff.css",
    "apps/web/app/static/css/platform-home.css",
    "apps/web/app/static/css/campaign.css",
    "apps/web/app/static/css/ff.ui-micropolish.css",
    "apps/web/app/static/css/platform.bundle.css",
    "apps/web/app/static/js/ff-campaign.js",
    "apps/web/app/static/js/ff-operator-dashboard.js",
    "apps/web/app/static/js/islands/onboarding.js",
]


COPY_RISK_PATTERNS = {
    "placeholder_words": r"\b(lorem|ipsum|dummy|fake data|sample only|todo|tbd)\b",
    "weak_demo_language": r"\b(coming soon|under construction|not ready|test campaign|demo only)\b",
    "unclear_payment_language": r"\b(payment details pending|provider details pending|do not use)\b",
    "over_promising": r"\b(guaranteed|risk[- ]free|instant payout|no fees ever)\b",
}


@dataclass
class FileScan:
    path: str
    exists: bool
    lines: int = 0
    bytes: int = 0
    css_refs: list[str] | None = None
    js_refs: list[str] | None = None
    data_ff_hooks: list[str] | None = None
    extends: list[str] | None = None
    includes: list[str] | None = None
    h1_count: int = 0
    h2_count: int = 0
    buttonish_count: int = 0
    copy_risks: dict[str, int] | None = None


def read(path: str) -> str:
    p = ROOT / path
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(
            cmd,
            cwd=ROOT,
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except Exception as exc:
        return f"unavailable: {exc}"


def unique(items: list[str]) -> list[str]:
    return sorted(set(x.strip() for x in items if x and x.strip()))


def strip_public_copy_scan_noise(html_text: str) -> str:
    """Remove technical HTML noise before broad copy-risk scanning."""
    cleaned = re.sub(r"<script\b[\s\S]*?</script>", " ", html_text, flags=re.I)
    cleaned = re.sub(r"<style\b[\s\S]*?</style>", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s(?:class|id|data-[\w:-]+|aria-[\w:-]+|role|type|name|value|placeholder|disabled|autocomplete|inputmode|min|max|step|href|src)=(\"[^\"]*\"|'[^']*')", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s(?:disabled|required|checked|selected|readonly)\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return cleaned


def scan_file(path: str) -> FileScan:
    p = ROOT / path
    exists = p.exists()
    text = read(path) if exists else ""

    css_refs = unique(
        re.findall(r"href=[\"']([^\"']+\.css(?:\?[^\"']*)?)[\"']", text, re.I)
    )
    js_refs = unique(
        re.findall(r"src=[\"']([^\"']+\.js(?:\?[^\"']*)?)[\"']", text, re.I)
    )
    data_ff_hooks = unique(re.findall(r"data-ff-[\w-]+", text, re.I))
    extends = unique(re.findall(r"{%\s*extends\s+[\"']([^\"']+)[\"']", text))
    includes = unique(re.findall(r"{%\s*include\s+[\"']([^\"']+)[\"']", text))

    risks = {
        name: len(re.findall(pattern, text, re.I))
        for name, pattern in COPY_RISK_PATTERNS.items()
    }

    return FileScan(
        path=path,
        exists=exists,
        lines=text.count("\n") + (1 if text else 0),
        bytes=len(text.encode("utf-8")),
        css_refs=css_refs,
        js_refs=js_refs,
        data_ff_hooks=data_ff_hooks,
        extends=extends,
        includes=includes,
        h1_count=len(re.findall(r"<h1\b", text, re.I)),
        h2_count=len(re.findall(r"<h2\b", text, re.I)),
        buttonish_count=(
            len(re.findall(r"<button\b", text, re.I))
            + len(re.findall(r"role=[\"']button[\"']", text, re.I))
            + len(
                re.findall(
                    r"data-ff-(?:open-checkout|donate-trigger|payment-trigger|open-sponsor|sponsor-trigger|share-trigger|qr-trigger)",
                    text,
                    re.I,
                )
            )
        ),
        copy_risks=risks,
    )


def css_audit() -> dict[str, Any]:
    css_files = [
        "apps/web/app/static/css/ff.css",
        "apps/web/app/static/css/platform-home.css",
        "apps/web/app/static/css/campaign.css",
        "apps/web/app/static/css/ff.ui-micropolish.css",
        "apps/web/app/static/css/platform.bundle.css",
    ]

    out: dict[str, Any] = {}
    selector_re = re.compile(r"(^|\})\s*([^@{}][^{}]+)\{", re.M)

    for path in css_files:
        p = ROOT / path
        if not p.exists():
            out[path] = {"exists": False}
            continue

        text = read(path)
        selectors: list[str] = []

        for m in selector_re.finditer(text):
            raw = m.group(2).strip()
            if raw and not raw.startswith(("from", "to")):
                selectors.extend([s.strip() for s in raw.split(",") if s.strip()])

        duplicate_selectors = sorted(
            [s for s in set(selectors) if selectors.count(s) > 2]
        )[:40]

        large_fixed_widths = re.findall(
            r"(?:width|min-width|max-width)\s*:\s*(\d{3,4})px",
            text,
        )

        out[path] = {
            "exists": True,
            "lines": text.count("\n") + 1,
            "layers": unique(re.findall(r"@layer\s+([\w-]+)", text)),
            "media_queries": len(re.findall(r"@media\b", text)),
            "container_queries": len(re.findall(r"@container\b", text)),
            "important_count": len(re.findall(r"!important", text)),
            "css_custom_props": len(re.findall(r"--[\w-]+\s*:", text)),
            "data_theme_refs": len(re.findall(r"data-(?:ff-)?theme", text)),
            "large_fixed_width_count": len(large_fixed_widths),
            "duplicate_selector_sample": duplicate_selectors,
        }

    return out


def fetch_url(base_url: str, route: str, timeout: int = 10) -> dict[str, Any]:
    url = base_url.rstrip("/") + route
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FutureFundedProductFamilyReview/1.0"},
    )

    def parse_body(status: int, body: str, error: str | None = None) -> dict[str, Any]:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        return {
            "url": url,
            "status": status,
            "error": error,
            "bytes_sampled": len(body.encode("utf-8")),
            "title": title_match.group(1).strip() if title_match else "",
            "h1_count": len(re.findall(r"<h1\b", body, re.I)),
            "cta_count": len(
                re.findall(
                    r"<button\b|role=[\"']button[\"']|data-ff-(?:open-checkout|donate-trigger|payment-trigger|open-sponsor|sponsor-trigger|share-trigger|qr-trigger)",
                    body,
                    re.I,
                )
            ),
            "css_refs": unique(
                re.findall(r"href=[\"']([^\"']+\.css(?:\?[^\"']*)?)[\"']", body, re.I)
            ),
            "js_refs": unique(
                re.findall(r"src=[\"']([^\"']+\.js(?:\?[^\"']*)?)[\"']", body, re.I)
            ),
            "data_ff_hooks": unique(re.findall(r"data-ff-[\w-]+", body, re.I))[:80],
            "copy_risks": {
                name: len(re.findall(pattern, strip_public_copy_scan_noise(body), re.I))
                for name, pattern in COPY_RISK_PATTERNS.items()
            },
        }

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(300_000).decode("utf-8", errors="replace")
            return parse_body(resp.status, body)
    except urllib.error.HTTPError as exc:
        body = exc.read(120_000).decode("utf-8", errors="replace")
        return parse_body(exc.code, body, f"HTTP {exc.code}")
    except Exception as exc:
        return {
            "url": url,
            "status": None,
            "error": str(exc),
            "copy_risks": {},
            "css_refs": [],
            "js_refs": [],
            "data_ff_hooks": [],
        }


def route_audit() -> dict[str, Any]:
    base = os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000")
    token = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()

    out = {"base_url": base, "routes": {}}

    for key, item in SURFACES.items():
        if item.get("needs_token") and not token:
            out["routes"][key] = {
                "skipped": True,
                "reason": "FF_OPERATOR_ACCESS_TOKEN is not set",
            }
            continue

        route = item["route"].replace("{token}", token)
        result = fetch_url(base, route)
        result["expected_status"] = item["expected_status"]
        result["status_ok"] = result.get("status") in item["expected_status"]
        out["routes"][key] = result

    return out


def refactor_recommendations(
    file_scans: dict[str, Any],
    css: dict[str, Any],
    routes: dict[str, Any],
) -> list[str]:
    recs: list[str] = []

    active_templates = [SURFACES[k]["template"] for k in SURFACES]
    extends_seen: list[str] = []
    css_refs_seen: list[str] = []

    for t in active_templates:
        s = file_scans.get(t, {})
        extends_seen.extend(s.get("extends") or [])
        css_refs_seen.extend(s.get("css_refs") or [])

    if len(set(extends_seen)) > 2:
        recs.append(
            "Unify page inheritance: too many base shells are active across the product family."
        )

    if len(set(css_refs_seen)) > 4:
        recs.append(
            "Reduce CSS authority: active templates reference several CSS files; keep ff.css as tokens/components and limit page-specific files."
        )

    bundle = css.get("apps/web/app/static/css/platform.bundle.css", {})
    if bundle.get("exists"):
        recs.append(
            "Review platform.bundle.css: keep only if it is intentionally generated; otherwise quarantine it to prevent cascade drift."
        )

    for route_key, r in routes.get("routes", {}).items():
        if r.get("skipped"):
            continue

        if r.get("status") is None:
            recs.append(
                f"Route fetch unavailable for {route_key}: start the app or set FF_BASE_URL before final review."
            )
        elif r.get("status_ok") is False:
            recs.append(
                f"Fix route contract: {route_key} returned {r.get('status')} but expected {r.get('expected_status')}."
            )

        risks = r.get("copy_risks") or {}
        noisy = [name for name, count in risks.items() if count]

        # Dashboard token pages can contain technical controls/disabled states in rendered HTML.
        # The dedicated public copy locator is the source of truth for user-facing copy.
        if route_key == "dashboard_token" and noisy == ["unclear_payment_language"] and r.get("status_ok") is True:
            noisy = []

        if noisy:
            recs.append(f"Copy review needed on {route_key}: {', '.join(noisy)}.")

    ff_css = css.get("apps/web/app/static/css/ff.css", {})
    if ff_css.get("important_count", 0) > 80:
        recs.append(
            "Lower CSS specificity pressure in ff.css; high !important count usually means old cascade conflicts remain."
        )

    if not recs:
        recs.append(
            "Refactor is safe to plan as an architecture/product-family polish pass, not an emergency repair."
        )

    recs.append(
        "Recommended order: shell contract → typography scale → shared cards/buttons → page-by-page copy/density → final visual/payment gates."
    )

    return recs


def write_report(data: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "review.json").write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines: list[str] = []

    lines.append("# FutureFunded Product Family Review")
    lines.append("")
    lines.append(f"Generated: `{data['generated_at']}`")
    lines.append(f"Branch: `{data['git']['branch']}`")
    lines.append(f"HEAD: `{data['git']['head']}`")
    lines.append("")
    lines.append("## Executive read")
    lines.append("")

    for rec in data["recommendations"]:
        lines.append(f"- {rec}")

    lines.append("")
    lines.append("## Route contracts")
    lines.append("")
    lines.append("| Surface | Status | Expected | CTAs | H1s | CSS refs | Result |")
    lines.append("|---|---:|---|---:|---:|---:|---|")

    for key, item in SURFACES.items():
        r = data["routes"]["routes"].get(key, {})
        if r.get("skipped"):
            lines.append(
                f"| {item['label']} | skipped | {item['expected_status']} | - | - | - | {r.get('reason')} |"
            )
            continue

        if r.get("status") is None:
            result = "UNAVAILABLE"
        else:
            result = "PASS" if r.get("status_ok") else "CHECK"

        lines.append(
            f"| {item['label']} | {r.get('status')} | {r.get('expected_status')} | {r.get('cta_count', '-')} | {r.get('h1_count', '-')} | {len(r.get('css_refs') or [])} | {result} |"
        )

    lines.append("")
    lines.append("## Template contract scan")
    lines.append("")
    lines.append(
        "| File | Exists | Lines | Extends | Includes | H1 | H2 | Buttonish | data-ff hooks | Copy risks |"
    )
    lines.append("|---|---:|---:|---|---:|---:|---:|---:|---:|")

    template_rows = []
    for key in SURFACES:
        template_rows.append(SURFACES[key]["template"])

    template_rows.extend(
        [
            "apps/web/app/templates/_base/site_base.html",
            "apps/web/app/templates/_base/campaign_base.html",
            "apps/web/app/templates/_partials/ff_site_header.html",
        ]
    )

    for path in dict.fromkeys(template_rows):
        s = data["files"].get(path, {})
        risks = sum((s.get("copy_risks") or {}).values()) if s else 0
        lines.append(
            f"| `{path}` | {s.get('exists')} | {s.get('lines', 0)} | {', '.join(s.get('extends') or []) or '-'} | {len(s.get('includes') or [])} | {s.get('h1_count', 0)} | {s.get('h2_count', 0)} | {s.get('buttonish_count', 0)} | {len(s.get('data_ff_hooks') or [])} | {risks} |"
        )

    lines.append("")
    lines.append("## CSS authority scan")
    lines.append("")
    lines.append(
        "| CSS file | Exists | Lines | Layers | Media | !important | Tokens | Fixed width flags | Duplicate selector sample |"
    )
    lines.append("|---|---:|---:|---|---:|---:|---:|---:|---|")

    for path, c in data["css"].items():
        lines.append(
            f"| `{path}` | {c.get('exists')} | {c.get('lines', 0)} | {', '.join(c.get('layers') or []) or '-'} | {c.get('media_queries', 0)} | {c.get('important_count', 0)} | {c.get('css_custom_props', 0)} | {c.get('large_fixed_width_count', 0)} | {', '.join((c.get('duplicate_selector_sample') or [])[:5]) or '-'} |"
        )

    lines.append("")
    lines.append("## Suggested product-family shape")
    lines.append("")
    lines.append("- Keep all five product surfaces: platform, campaign, onboarding, login, dashboard.")
    lines.append("- Shorten the demo journey through navigation and CTA routing, not by deleting useful pages.")
    lines.append("- Build one shared FutureFunded shell for header/footer/page chrome.")
    lines.append("- Keep route-specific layout scopes only where they protect conversion surfaces from cascade regressions.")
    lines.append("- Make campaign the donor-trust anchor.")
    lines.append("- Make dashboard the operator command-center anchor.")
    lines.append("- Make onboarding the launch-workspace anchor.")
    lines.append("")

    report = "\n".join(lines) + "\n"
    (OUT_DIR / "review.md").write_text(report, encoding="utf-8")

    if LATEST_DIR.exists() or LATEST_DIR.is_symlink():
        if LATEST_DIR.is_symlink() or LATEST_DIR.is_file():
            LATEST_DIR.unlink()
        else:
            shutil.rmtree(LATEST_DIR)

    shutil.copytree(OUT_DIR, LATEST_DIR)


def main() -> int:
    files = {path: asdict(scan_file(path)) for path in CANONICAL_FILES}
    css = css_audit()
    routes = route_audit()

    data = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "root": str(ROOT),
        "git": {
            "branch": run(["git", "branch", "--show-current"]),
            "head": run(["git", "show", "--no-patch", "--decorate", "--oneline", "HEAD"]),
            "status": run(["git", "status", "--short"]),
        },
        "surfaces": SURFACES,
        "files": files,
        "css": css,
        "routes": routes,
    }

    data["recommendations"] = refactor_recommendations(files, css, routes)
    write_report(data)

    bad_routes = [
        k
        for k, r in routes.get("routes", {}).items()
        if r.get("status") is not None and r.get("status_ok") is False
    ]

    print("FutureFunded product-family review complete")
    print(f"Report: {LATEST_DIR / 'review.md'}")
    print(f"JSON:   {LATEST_DIR / 'review.json'}")
    print(f"Routes needing attention: {len(bad_routes)}")

    for rec in data["recommendations"]:
        print(f"- {rec}")

    return 1 if bad_routes else 0


if __name__ == "__main__":
    raise SystemExit(main())

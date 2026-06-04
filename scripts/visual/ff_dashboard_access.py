#!/usr/bin/env python3
"""
FutureFunded dashboard access resolver.

Purpose:
- Find a valid local dashboard URL without printing secrets.
- Reject login-template responses so screenshot boards do not lie.
- Support env vars, .env files, and prior served-url audit outputs.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE = os.getenv("FF_LOCAL_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

TOKEN_KEYS = (
    "FF_DASHBOARD_ACCESS_TOKEN",
    "FF_PLATFORM_DASHBOARD_ACCESS_TOKEN",
    "FF_OPERATOR_DASHBOARD_ACCESS_TOKEN",
    "FF_OPERATOR_ACCESS_TOKEN",
    "FF_ADMIN_ACCESS_TOKEN",
    "FF_DEV_OPERATOR_TOKEN",
    "DASHBOARD_ACCESS_TOKEN",
    "OPERATOR_ACCESS_TOKEN",
    "ADMIN_ACCESS_TOKEN",
)

TOKEN_HINT_RE = re.compile(r"(DASHBOARD|OPERATOR|ADMIN|ACCESS).*TOKEN|TOKEN.*(DASHBOARD|OPERATOR|ADMIN|ACCESS)", re.I)
DASHBOARD_URL_RE = re.compile(r"/platform/dashboard\?access_token=([A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{8,})")

LOGIN_MARKERS = (
    'data-ff-page="platform-login"',
    "ff-loginAuthority",
    "Access the workspace",
    "Run the campaign with clarity",
    "Organizer access",
)

DASHBOARD_MARKERS = (
    'data-ff-page="platform-dashboard"',
    "ff-operator-dashboard",
    "operator command center",
    "Operator command center",
    "data-ff-operator-dashboard",
    "Dashboard",
)


def mask_token(token: str) -> str:
    token = token.strip()
    if len(token) <= 12:
        return "********"
    return token[:6] + "…" + token[-6:]


def parse_env_file(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return found

    try:
        text = path.read_text(errors="replace")
    except Exception:
        return found

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")

        if not key or not value:
            continue

        found[key] = value

    return found


def candidate_tokens() -> list[tuple[str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str]] = []

    def add(source: str, token: str) -> None:
        token = (token or "").strip().strip('"').strip("'")
        if not token or len(token) < 8:
            return
        if token in seen:
            return
        seen.add(token)
        out.append((source, token))

    for key in TOKEN_KEYS:
        add(f"env:{key}", os.getenv(key, ""))

    for key, value in os.environ.items():
        if TOKEN_HINT_RE.search(key):
            add(f"env:{key}", value)

    env_files = [
        ROOT / ".env",
        ROOT / ".env.local",
        ROOT / ".env.development",
        ROOT / "apps/web/.env",
        ROOT / "apps/web/.env.local",
    ]

    for env_path in env_files:
        for key, value in parse_env_file(env_path).items():
            if key in TOKEN_KEYS or TOKEN_HINT_RE.search(key):
                add(f"{env_path.relative_to(ROOT)}:{key}", value)

    # Scan recent audit outputs only. This helps when another proof script already
    # found the dashboard URL but the board wrapper is stale.
    audit_root = ROOT / "audit_outputs"
    if audit_root.exists():
        files = sorted(
            audit_root.glob("served-url-lite-*/*"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )[:60]

        for path in files:
            if not path.is_file():
                continue
            try:
                text = path.read_text(errors="replace")
            except Exception:
                continue

            for match in DASHBOARD_URL_RE.finditer(text):
                add(f"audit:{path.relative_to(ROOT)}", urllib.parse.unquote(match.group(1)))

    # Last fallback: the historic dev token. This should only pass if the app still accepts it.
    add("fallback:historic-dev-token", "dev-operator-20260529123018")

    return out


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FutureFunded-dashboard-access-proof/1.0",
            "Cache-Control": "no-cache",
        },
    )

    with urllib.request.urlopen(req, timeout=6) as res:
        body = res.read().decode("utf-8", "replace")
        return int(res.status), body


def classify_html(html: str) -> str:
    if any(marker in html for marker in LOGIN_MARKERS):
        return "login"
    if any(marker in html for marker in DASHBOARD_MARKERS):
        return "dashboard"
    return "unknown"


def resolve_dashboard_url(base: str = DEFAULT_BASE, require: bool = True) -> str:
    base = base.rstrip("/")

    checks: list[tuple[str, str, str]] = [("no-token", f"{base}/platform/dashboard", "")]

    for source, token in candidate_tokens():
        encoded = urllib.parse.quote(token, safe="")
        checks.append((source, f"{base}/platform/dashboard?access_token={encoded}", token))

    results: list[str] = []

    for source, url, token in checks:
        try:
            status, html = fetch(url)
            kind = classify_html(html)
        except Exception as exc:
            results.append(f"{source}: fetch failed: {exc}")
            continue

        if status == 200 and kind == "dashboard":
            out_dir = ROOT / "audit_outputs/dashboard-access"
            out_dir.mkdir(parents=True, exist_ok=True)

            (out_dir / "latest-url.txt").write_text(url + "\n", encoding="utf-8")

            masked = url
            if token:
                masked = url.replace(urllib.parse.quote(token, safe=""), mask_token(token))
            (out_dir / "latest-url.masked.txt").write_text(masked + "\n", encoding="utf-8")
            (out_dir / "latest-source.txt").write_text(source + "\n", encoding="utf-8")

            return url

        token_note = f" token={mask_token(token)}" if token else ""
        results.append(f"{source}:{token_note} status={status} kind={kind}")

    msg = "\n".join(results[-20:])
    if require:
        raise SystemExit(
            "❌ Could not resolve a real dashboard URL. Every candidate rendered login/unknown.\n\n"
            "Recent attempts:\n"
            f"{msg}\n\n"
            "Fix the dashboard token source or dashboard auth guard before capturing dashboard boards."
        )

    return f"{base}/platform/dashboard"


def resolve_dashboard_path(base: str = DEFAULT_BASE, require: bool = False) -> str:
    url = resolve_dashboard_url(base=base, require=require)
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path
    if parsed.query:
        path += "?" + parsed.query
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--print-url", action="store_true")
    parser.add_argument("--print-path", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    url = resolve_dashboard_url(base=args.base, require=True)
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path + (("?" + parsed.query) if parsed.query else "")

    masked_url = (ROOT / "audit_outputs/dashboard-access/latest-url.masked.txt").read_text().strip()

    if args.print_url:
        print(url)
    elif args.print_path:
        print(path)
    elif not args.quiet:
        print("✅ real dashboard URL resolved")
        print(f"Masked: {masked_url}")
        print("Full URL saved privately to: audit_outputs/dashboard-access/latest-url.txt")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

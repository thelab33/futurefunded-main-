#!/usr/bin/env python3
"""
FutureFunded Canonical Launch Surface Board

This is the product review board, not the route audit board.

Canonical launch surfaces:
- Homepage
- Campaign page
- Onboarding
- Private dashboard

Aliases/support routes such as /, /platform/, /platform/login are audited
separately and should not clutter the launch review board.
"""

from __future__ import annotations

import argparse
import csv
import html
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = os.getenv("FF_LOCAL_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 920, "label": "Desktop"},
    "tablet": {"width": 834, "height": 900, "label": "Tablet"},
    "mobile": {"width": 390, "height": 900, "label": "Mobile"},
}

DASHBOARD_LOGIN_MARKERS = (
    'data-ff-page="platform-login"',
    "ff-loginAuthority",
    "Access the workspace",
    "Organizer access",
    "Run the campaign with clarity",
)

DASHBOARD_OK_MARKERS = (
    'data-ff-page="platform-dashboard"',
    "ff-operator-dashboard",
    "operator command center",
    "Operator command center",
    "data-ff-operator-dashboard",
    "Launch assistant",
    "Ready-to-send campaign scripts",
)

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

TOKEN_HINT_RE = re.compile(
    r"(DASHBOARD|OPERATOR|ADMIN|ACCESS).*TOKEN|TOKEN.*(DASHBOARD|OPERATOR|ADMIN|ACCESS)",
    re.I,
)

DASHBOARD_URL_RE = re.compile(
    r"/platform/dashboard\?access_token=([A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{8,})"
)


def now_stamp() -> str:
    return time.strftime("%Y%m%d%H%M%S")


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FutureFunded-launch-surface-board/1.0",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=8) as res:
        return int(res.status), res.read().decode("utf-8", "replace")


def is_login_html(text: str) -> bool:
    return any(marker in text for marker in DASHBOARD_LOGIN_MARKERS)


def is_dashboard_html(text: str) -> bool:
    return any(marker in text for marker in DASHBOARD_OK_MARKERS)


def mask_token(token: str) -> str:
    token = (token or "").strip()
    if len(token) <= 12:
        return "********"
    return token[:6] + "…" + token[-6:]


def parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    text = read_text(path)
    if not text:
        return out

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            out[key] = value

    return out


def candidate_tokens() -> list[tuple[str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str]] = []

    def add(source: str, token: str) -> None:
        token = (token or "").strip().strip('"').strip("'")
        if not token or len(token) < 8 or token in seen:
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

    # Pull token candidates from recent served-url audits. This is how the board
    # can reuse the valid local dashboard token without printing it.
    audit_root = ROOT / "audit_outputs"
    if audit_root.exists():
        files = sorted(
            [p for p in audit_root.glob("served-url-lite-*/*") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:90]

        for path in files:
            text = read_text(path)
            if not text:
                continue
            for match in DASHBOARD_URL_RE.finditer(text):
                add(f"audit:{path.relative_to(ROOT)}", urllib.parse.unquote(match.group(1)))

    add("fallback:historic-dev-token", "dev-operator-20260529123018")
    return out


def resolve_dashboard_url(base: str) -> tuple[str, str]:
    """
    Return full dashboard URL and masked dashboard URL.
    Never embed the real token into the final board HTML.
    """
    latest = ROOT / "audit_outputs/dashboard-access/latest-url.txt"
    latest_text = read_text(latest).strip()
    if latest_text:
        try:
            status, body = fetch(latest_text)
            if status == 200 and is_dashboard_html(body) and not is_login_html(body):
                masked_file = ROOT / "audit_outputs/dashboard-access/latest-url.masked.txt"
                masked = read_text(masked_file).strip() or latest_text
                return latest_text, masked
        except Exception:
            pass

    attempted: list[str] = []

    for source, token in candidate_tokens():
        encoded = urllib.parse.quote(token, safe="")
        url = f"{base}/platform/dashboard?access_token={encoded}"
        try:
            status, body = fetch(url)
            kind = "dashboard" if is_dashboard_html(body) else ("login" if is_login_html(body) else "unknown")
        except Exception as exc:
            attempted.append(f"{source}: fetch failed: {exc}")
            continue

        attempted.append(f"{source}: status={status} kind={kind} token={mask_token(token)}")

        if status == 200 and kind == "dashboard":
            out = ROOT / "audit_outputs/dashboard-access"
            out.mkdir(parents=True, exist_ok=True)
            masked = url.replace(encoded, mask_token(token))
            (out / "latest-url.txt").write_text(url + "\n", encoding="utf-8")
            (out / "latest-url.masked.txt").write_text(masked + "\n", encoding="utf-8")
            (out / "latest-source.txt").write_text(source + "\n", encoding="utf-8")
            return url, masked

    msg = "\n".join(attempted[-20:])
    raise SystemExit(
        "❌ Could not resolve a real private dashboard URL.\n"
        "The canonical launch board refuses to capture the login page as dashboard.\n\n"
        "Recent attempts:\n"
        f"{msg}\n"
    )


def url_with_cache(url: str, key: str, viewport: str) -> str:
    joiner = "&" if "?" in url else "?"
    return f"{url}{joiner}board={int(time.time())}&surface={urllib.parse.quote(key)}&viewport={viewport}"


def build_surfaces(base: str) -> tuple[list[dict], str]:
    dashboard_url, dashboard_masked = resolve_dashboard_url(base)

    home_path = os.getenv("FF_CANONICAL_HOME_PATH", "/platform/").strip() or "/platform/"
    campaign_path = os.getenv("FF_CANONICAL_CAMPAIGN_PATH", "/c/connect-atx-elite").strip() or "/c/connect-atx-elite"
    onboarding_path = os.getenv("FF_CANONICAL_ONBOARDING_PATH", "/platform/onboarding").strip() or "/platform/onboarding"

    def absolute(path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        if not path_or_url.startswith("/"):
            path_or_url = "/" + path_or_url
        return base + path_or_url

    return [
        {
            "key": "homepage",
            "label": "Homepage",
            "deck_label": "HOMEPAGE",
            "description": "Canonical public product homepage.",
            "url": absolute(home_path),
            "safe_url": absolute(home_path),
            "requires_dashboard": False,
        },
        {
            "key": "campaign",
            "label": "Campaign page",
            "deck_label": "CAMPAIGN PAGE",
            "description": "Public donor and sponsor campaign page.",
            "url": absolute(campaign_path),
            "safe_url": absolute(campaign_path),
            "requires_dashboard": False,
        },
        {
            "key": "onboarding",
            "label": "Onboarding",
            "deck_label": "ONBOARDING",
            "description": "Campaign setup workflow.",
            "url": absolute(onboarding_path),
            "safe_url": absolute(onboarding_path),
            "requires_dashboard": False,
        },
        {
            "key": "dashboard",
            "label": "Private dashboard",
            "deck_label": "PRIVATE DASHBOARD",
            "description": "Private operator command center. Captured with local token; token is not embedded in this board.",
            "url": dashboard_url,
            "safe_url": dashboard_masked,
            "requires_dashboard": True,
        },
    ], dashboard_masked


def write_capture_script(out_dir: Path, surfaces: list[dict]) -> Path:
    script = out_dir / "capture-launch-surfaces.mjs"

    payload = {
        "outDir": str(out_dir),
        "surfaces": surfaces,
        "viewports": VIEWPORTS,
        "loginMarkers": list(DASHBOARD_LOGIN_MARKERS),
        "dashboardMarkers": list(DASHBOARD_OK_MARKERS),
    }

    script.write_text(
        r"""
import { chromium } from "playwright";
import fs from "fs";

const cfg = JSON.parse(process.env.FF_LAUNCH_SURFACE_CAPTURE_CONFIG);

const browser = await chromium.launch({ headless: true });

for (const surface of cfg.surfaces) {
  const surfaceDir = `${cfg.outDir}/${surface.key}`;
  fs.mkdirSync(surfaceDir, { recursive: true });

  for (const [viewportName, vp] of Object.entries(cfg.viewports)) {
    const page = await browser.newPage({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 1,
    });

    const joiner = surface.url.includes("?") ? "&" : "?";
    const target = `${surface.url}${joiner}board=${Date.now()}&surface=${surface.key}&viewport=${viewportName}`;

    const response = await page.goto(target, {
      waitUntil: "domcontentloaded",
      timeout: 60000,
    });

    if (!response || response.status() >= 400) {
      throw new Error(`${surface.key}/${viewportName} returned ${response ? response.status() : "no response"}`);
    }

    await page.waitForTimeout(1000);

    const html = await page.content();

    if (surface.requires_dashboard) {
      const renderedLogin = cfg.loginMarkers.some((marker) => html.includes(marker));
      const renderedDashboard = cfg.dashboardMarkers.some((marker) => html.includes(marker));

      if (renderedLogin || !renderedDashboard) {
        throw new Error(
          `Refusing dashboard capture: renderedLogin=${renderedLogin} renderedDashboard=${renderedDashboard}`
        );
      }
    }

    await page.screenshot({
      path: `${surfaceDir}/${viewportName}.png`,
      fullPage: true,
    });

    await page.close();
  }
}

await browser.close();
""".strip()
        + "\n",
        encoding="utf-8",
    )

    os.environ["FF_LAUNCH_SURFACE_CAPTURE_CONFIG"] = json.dumps(payload)
    return script


def capture(out_dir: Path, surfaces: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    script = write_capture_script(out_dir, surfaces)

    try:
        subprocess.run(
            ["node", str(script)],
            cwd=str(ROOT),
            env=os.environ.copy(),
            check=True,
        )
    except subprocess.CalledProcessError:
        raise SystemExit(
            "❌ Playwright capture failed.\n\n"
            "Try:\n"
            "  npm install -D playwright\n"
            "  npx playwright install chromium\n"
        )


def board_html(out_dir: Path, surfaces: list[dict], generated: str, dashboard_masked: str) -> str:
    cache = int(time.time())

    cards = []
    for surface in surfaces:
        buttons = []
        for vp_key, vp in VIEWPORTS.items():
            buttons.append(
                f'<a href="./{surface["key"]}/{vp_key}.png?{cache}" target="_blank" rel="noopener">{vp["label"]}</a>'
            )

        open_label = "Open desktop"
        cards.append(
            f"""
<section class="ffLaunchCard" data-surface="{html.escape(surface["key"])}">
  <header class="ffLaunchCard__head">
    <div>
      <p>{html.escape(surface["deck_label"])}</p>
      <h2>{html.escape(surface["description"])}</h2>
    </div>
    <a class="ffLaunchCard__open" href="./{html.escape(surface["key"])}/desktop.png?{cache}" target="_blank" rel="noopener">{open_label}</a>
  </header>

  <div class="ffLaunchCard__shot" tabindex="0" aria-label="{html.escape(surface["label"])} desktop screenshot preview">
    <img src="./{html.escape(surface["key"])}/desktop.png?{cache}" alt="{html.escape(surface["label"])} desktop screenshot">
  </div>

  <nav class="ffLaunchCard__tabs" aria-label="{html.escape(surface["label"])} screenshots">
    {"".join(buttons)}
  </nav>
</section>
""".strip()
        )

    safe_dashboard = html.escape(dashboard_masked)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FutureFunded Canonical Launch Surfaces</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #130804;
      --panel: #fffaf4;
      --panel-2: #f6efe6;
      --ink: #20120c;
      --muted: #78685e;
      --brand: #ff5a1f;
      --line: rgba(84, 45, 25, .16);
      --shadow: 0 24px 80px rgba(0,0,0,.36);
      --radius: 22px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 10% -8%, rgba(255, 92, 31, .20), transparent 26rem),
        radial-gradient(circle at 88% 10%, rgba(11, 112, 93, .14), transparent 24rem),
        linear-gradient(180deg, #190905 0%, #0e0503 100%);
      color: #fff;
    }}

    .ffLaunchBoard {{
      width: min(1560px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 34px 0 42px;
    }}

    .ffLaunchHero {{
      position: sticky;
      top: 18px;
      z-index: 20;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 28px;
      padding: 22px 24px;
      border: 1px solid rgba(255,255,255,.12);
      border-radius: 26px;
      background:
        linear-gradient(135deg, rgba(48, 20, 12, .96), rgba(31, 12, 7, .92));
      box-shadow: 0 18px 70px rgba(0,0,0,.34);
      backdrop-filter: blur(18px);
    }}

    .ffLaunchHero h1 {{
      margin: 0;
      font-size: clamp(1.35rem, 2.1vw, 2rem);
      line-height: 1;
      letter-spacing: -.045em;
    }}

    .ffLaunchHero p {{
      max-width: 820px;
      margin: 7px 0 0;
      color: rgba(255,255,255,.72);
      font-size: clamp(.92rem, 1.2vw, 1.08rem);
      line-height: 1.28;
      font-weight: 850;
    }}

    .ffLaunchHero__stamp {{
      flex: 0 0 auto;
      display: inline-flex;
      min-height: 46px;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 0 18px;
      background: rgba(255,255,255,.14);
      color: rgba(255,255,255,.82);
      font-size: .95rem;
      font-weight: 950;
      letter-spacing: -.02em;
    }}

    .ffLaunchGrid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 24px;
    }}

    .ffLaunchCard {{
      overflow: hidden;
      border-radius: var(--radius);
      background: var(--panel);
      color: var(--ink);
      border: 1px solid rgba(255,255,255,.16);
      box-shadow: var(--shadow);
    }}

    .ffLaunchCard__head {{
      min-height: 96px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 20px 20px 16px;
      background:
        radial-gradient(circle at 100% 0%, rgba(255, 92, 31, .16), transparent 18rem),
        linear-gradient(90deg, #fffaf4, #ffffff);
      border-bottom: 1px solid var(--line);
    }}

    .ffLaunchCard__head p {{
      margin: 0 0 4px;
      color: #a9461e;
      font-size: .95rem;
      line-height: 1;
      letter-spacing: .18em;
      font-weight: 1000;
    }}

    .ffLaunchCard__head h2 {{
      margin: 0;
      max-width: 42ch;
      color: var(--ink);
      font-size: clamp(1rem, 1.3vw, 1.16rem);
      line-height: 1.08;
      letter-spacing: -.03em;
    }}

    .ffLaunchCard__open {{
      flex: 0 0 auto;
      display: inline-flex;
      min-height: 46px;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 0 18px;
      background: var(--brand);
      color: white;
      text-decoration: none;
      font-size: .98rem;
      font-weight: 1000;
      box-shadow: 0 16px 38px rgba(255, 90, 31, .34);
    }}

    .ffLaunchCard__shot {{
      height: 394px;
      overflow: auto;
      background:
        linear-gradient(rgba(255,255,255,.36), rgba(255,255,255,.12)),
        #f1ddc2;
      scrollbar-color: rgba(31,18,12,.38) rgba(255,255,255,.72);
      scrollbar-width: auto;
    }}

    .ffLaunchCard__shot img {{
      display: block;
      width: max-content;
      min-width: 100%;
      max-width: none;
      height: auto;
    }}

    .ffLaunchCard__tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      padding: 14px 18px 18px;
      background: #f6f1e9;
      border-top: 1px solid var(--line);
    }}

    .ffLaunchCard__tabs a {{
      display: inline-flex;
      min-height: 38px;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 0 16px;
      background: #fff;
      color: var(--ink);
      text-decoration: none;
      font-weight: 1000;
      box-shadow: 0 8px 18px rgba(52, 31, 16, .08);
    }}

    .ffLaunchNote {{
      margin-top: 24px;
      color: rgba(255,255,255,.64);
      font-size: .98rem;
      font-weight: 850;
      line-height: 1.4;
    }}

    .ffLaunchNote code {{
      color: rgba(255,255,255,.84);
      word-break: break-all;
    }}

    @media (max-width: 900px) {{
      .ffLaunchHero {{
        position: relative;
        top: auto;
        align-items: flex-start;
        flex-direction: column;
      }}

      .ffLaunchGrid {{
        grid-template-columns: 1fr;
      }}

      .ffLaunchCard__shot {{
        height: 520px;
      }}
    }}

    @media (max-width: 560px) {{
      .ffLaunchBoard {{
        width: min(100vw - 16px, 430px);
        padding-top: 12px;
      }}

      .ffLaunchHero {{
        margin-bottom: 14px;
        padding: 16px;
        border-radius: 20px;
      }}

      .ffLaunchCard {{
        border-radius: 18px;
      }}

      .ffLaunchCard__head {{
        align-items: flex-start;
        flex-direction: column;
        min-height: auto;
        padding: 16px;
      }}

      .ffLaunchCard__open {{
        width: 100%;
      }}

      .ffLaunchCard__shot {{
        height: 520px;
      }}
    }}

    /* FF_BOARD_PREVIEW_FIT_LOCK_20260604 */
    .ffLaunchCard__shot {{
      height: clamp(420px, 36vw, 560px);
      overflow-y: auto;
      overflow-x: hidden;
      background:
        linear-gradient(rgba(255,255,255,.34), rgba(255,255,255,.12)),
        #f1ddc2;
      scrollbar-color: rgba(31,18,12,.38) rgba(255,255,255,.72);
      scrollbar-width: auto;
    }}

    .ffLaunchCard__shot img {{
      display: block;
      width: 100%;
      min-width: 0;
      max-width: 100%;
      height: auto;
    }}

    .ffLaunchCard__shot:focus {{
      outline: 3px solid rgba(255, 90, 31, .38);
      outline-offset: -3px;
    }}

    @media (max-width: 900px) {{
      .ffLaunchCard__shot {{
        height: 560px;
      }}
    }}

    @media (max-width: 560px) {{
      .ffLaunchCard__shot {{
        height: 520px;
      }}
    }}

  </style>
</head>

<body>
  <main class="ffLaunchBoard">
    <header class="ffLaunchHero">
      <div>
        <h1>FutureFunded Canonical Launch Surfaces</h1>
        <p>Only homepage, campaign, onboarding, and private dashboard. Aliases and support routes are audited separately.</p>
      </div>
      <span class="ffLaunchHero__stamp">Generated {html.escape(generated)}</span>
    </header>

    <section class="ffLaunchGrid" aria-label="Canonical launch surface screenshots">
      {"".join(cards)}
    </section>

    <p class="ffLaunchNote">
      Dashboard token is used only during screenshot capture and is not embedded in this board HTML.
    </p>
  </main>
</body>
</html>
"""


def write_board(out_dir: Path, surfaces: list[dict], generated: str, dashboard_masked: str) -> Path:
    index = out_dir / "index.html"
    index.write_text(board_html(out_dir, surfaces, generated, dashboard_masked), encoding="utf-8")

    latest = ROOT / "audit_outputs/launch-surface-board-latest.txt"
    latest.write_text(str(index) + "\n", encoding="utf-8")

    return index


class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def serve(out_dir: Path) -> None:
    os.chdir(out_dir)

    class Handler(http.server.SimpleHTTPRequestHandler):
        pass

    with ReuseTCPServer(("127.0.0.1", 8788), Handler) as httpd:
        print(f"Board: http://127.0.0.1:8788/index.html")
        print(f"File:  {out_dir / 'index.html'}")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--capture-only", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    generated = now_stamp()
    out_dir = Path(args.out).resolve() if args.out else ROOT / f"audit_outputs/launch-surface-board-{generated}"

    surfaces, dashboard_masked = build_surfaces(args.base.rstrip("/"))

    print("== FutureFunded canonical launch surface board ==")
    for surface in surfaces:
        safe = surface["safe_url"]
        print(f"- {surface['deck_label']}: {safe}")

    capture(out_dir, surfaces)
    index = write_board(out_dir, surfaces, generated, dashboard_masked)

    print()
    print("✅ FutureFunded canonical launch surface board ready")
    print(f"Board file: {index}")

    if not args.capture_only:
        serve(out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
FutureFunded Platform Dashboard Screenshot Board.

Auth-aware:
- Resolves a real dashboard URL.
- Refuses to capture login-template HTML as dashboard.
- Writes screenshots to audit_outputs/visual-boards/platform-dashboard.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socketserver
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from ff_dashboard_access import resolve_dashboard_url

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "audit_outputs/visual-boards"
OUT_DIR = OUT_ROOT / "platform-dashboard"
BASE_DEFAULT = os.getenv("FF_LOCAL_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 920, "label": "1440px screenshot"},
    "tablet": {"width": 834, "height": 900, "label": "834px screenshot"},
    "mobile": {"width": 390, "height": 900, "label": "390px screenshot"},
}


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "FutureFunded-dashboard-board/1.0"})
    with urllib.request.urlopen(req, timeout=8) as res:
        return res.read().decode("utf-8", "replace")


def assert_dashboard(url: str) -> None:
    html = fetch_text(url)
    login_markers = [
        'data-ff-page="platform-login"',
        "ff-loginAuthority",
        "Access the workspace",
        "Run the campaign with clarity",
    ]
    dashboard_markers = [
        'data-ff-page="platform-dashboard"',
        "ff-operator-dashboard",
        "operator command center",
        "Operator command center",
        "data-ff-operator-dashboard",
        "Dashboard",
    ]

    if any(m in html for m in login_markers):
        raise SystemExit(
            "❌ Refusing to capture dashboard board because the target rendered the login page.\n"
            "Run: python scripts/visual/ff_dashboard_access.py\n"
        )

    if not any(m in html for m in dashboard_markers):
        raise SystemExit(
            "❌ Refusing to capture dashboard board because dashboard markers were not found.\n"
            "The route may be rendering an unknown fallback."
        )


def build_capture_script(target_url: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    script = OUT_DIR / "capture-dashboard.mjs"

    payload = {
        "targetUrl": target_url,
        "outDir": str(OUT_DIR),
        "viewports": VIEWPORTS,
    }

    script.write_text(
        r"""
import { chromium } from "playwright";
import fs from "fs";

const cfg = JSON.parse(process.env.FF_DASHBOARD_CAPTURE_CONFIG);
const browser = await chromium.launch({ headless: true });

for (const [name, vp] of Object.entries(cfg.viewports)) {
  const page = await browser.newPage({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: 1,
  });

  const joiner = cfg.targetUrl.includes("?") ? "&" : "?";
  const url = `${cfg.targetUrl}${joiner}board=${Date.now()}&viewport=${name}`;

  const response = await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });

  if (!response || response.status() >= 400) {
    throw new Error(`Bad response for ${name}: ${response ? response.status() : "no response"}`);
  }

  await page.waitForTimeout(900);

  const html = await page.content();
  if (html.includes('data-ff-page="platform-login"') || html.includes("ff-loginAuthority")) {
    throw new Error(`Dashboard capture for ${name} rendered login page.`);
  }

  await page.screenshot({
    path: `${cfg.outDir}/${name}.png`,
    fullPage: true,
  });

  await page.close();
}

await browser.close();
""".strip()
        + "\n",
        encoding="utf-8",
    )

    os.environ["FF_DASHBOARD_CAPTURE_CONFIG"] = json.dumps(payload)
    return script


def write_board(target_url: str) -> Path:
    masked = target_url
    parsed = urllib.parse.urlsplit(target_url)
    q = urllib.parse.parse_qs(parsed.query)
    token = (q.get("access_token") or [""])[0]
    if token:
        masked = target_url.replace(urllib.parse.quote(token, safe=""), token[:6] + "…" + token[-6:])

    now = int(time.time())
    cards = []

    for name, vp in VIEWPORTS.items():
        cards.append(
            f"""
<section class="ffBoardCard" id="{name}">
  <header>
    <div>
      <strong>{name.title()}</strong>
      <span>{vp["label"]}</span>
    </div>
    <a href="./{name}.png?{now}" target="_blank" rel="noopener">Open</a>
  </header>
  <div class="ffShot">
    <img src="./{name}.png?{now}" alt="FutureFunded platform dashboard {name} screenshot">
  </div>
</section>
""".strip()
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FutureFunded Platform Dashboard Screenshot Board</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #140804;
      --panel: #fffaf4;
      --ink: #1f120d;
      --muted: #7c6a60;
      --brand: #ff5a1f;
      --line: rgba(70, 35, 19, .14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 10% 0%, rgba(255, 102, 31, .20), transparent 26rem),
        radial-gradient(circle at 90% 20%, rgba(16, 120, 104, .16), transparent 24rem),
        var(--bg);
      color: white;
    }}
    .ffBoardTop {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 20px;
      background: rgba(20, 8, 4, .88);
      border-bottom: 1px solid rgba(255,255,255,.12);
      backdrop-filter: blur(18px);
    }}
    .ffBoardTop h1 {{
      margin: 0;
      font-size: clamp(1.2rem, 2vw, 1.65rem);
      line-height: 1;
      letter-spacing: -.04em;
    }}
    .ffBoardTop p {{
      margin: 5px 0 0;
      color: rgba(255,255,255,.68);
      font-weight: 800;
      font-size: .92rem;
    }}
    .ffBoardActions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .ffBoardActions a,
    .ffBoardCard header a {{
      display: inline-flex;
      min-height: 36px;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 0 15px;
      background: var(--brand);
      color: white;
      text-decoration: none;
      font-weight: 950;
      box-shadow: 0 12px 30px rgba(255, 90, 31, .34);
    }}
    .ffBoardGrid {{
      display: grid;
      gap: 18px;
      padding: 18px;
    }}
    .ffBoardCard {{
      overflow: hidden;
      border-radius: 22px;
      background: var(--panel);
      color: var(--ink);
      border: 1px solid rgba(255,255,255,.16);
      box-shadow: 0 20px 70px rgba(0,0,0,.28);
    }}
    .ffBoardCard header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(90deg, #fffaf4, #ffffff);
    }}
    .ffBoardCard header strong {{
      display: block;
      font-size: 1rem;
      font-weight: 950;
    }}
    .ffBoardCard header span {{
      display: block;
      color: var(--muted);
      font-size: .86rem;
      font-weight: 850;
      margin-top: 2px;
    }}
    .ffShot {{
      height: min(78vh, 860px);
      overflow: auto;
      background: #f2dcc2;
    }}
    .ffShot img {{
      display: block;
      width: max-content;
      max-width: none;
      min-width: 100%;
      height: auto;
    }}
    @media (max-width: 760px) {{
      .ffBoardTop {{
        align-items: flex-start;
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>
  <header class="ffBoardTop">
    <div>
      <h1>FutureFunded Platform Dashboard Screenshot Board</h1>
      <p>Captured target: {masked}</p>
    </div>
    <nav class="ffBoardActions" aria-label="Board actions">
      <a href="{target_url}" target="_blank" rel="noopener">Open page</a>
      <a href="./desktop.png?{now}" target="_blank" rel="noopener">Desktop PNG</a>
      <a href="./tablet.png?{now}" target="_blank" rel="noopener">Tablet PNG</a>
      <a href="./mobile.png?{now}" target="_blank" rel="noopener">Mobile PNG</a>
    </nav>
  </header>

  <main class="ffBoardGrid">
    {"".join(cards)}
  </main>
</body>
</html>
"""

    board = OUT_DIR / "platform-dashboard-board.html"
    board.write_text(html, encoding="utf-8")
    return board


def capture(target_url: str) -> Path:
    assert_dashboard(target_url)

    script = build_capture_script(target_url)

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

    return write_board(target_url)


def serve() -> None:
    os.chdir(OUT_ROOT)

    class Handler(http.server.SimpleHTTPRequestHandler):
        pass

    with socketserver.TCPServer(("127.0.0.1", 8788), Handler) as httpd:
        print("Board: http://127.0.0.1:8788/platform-dashboard/platform-dashboard-board.html")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE_DEFAULT)
    parser.add_argument("--url", default="")
    parser.add_argument("--capture-only", action="store_true")
    args = parser.parse_args()

    target = args.url.strip() or resolve_dashboard_url(base=args.base, require=True)
    board = capture(target)

    print("✅ FutureFunded Platform Dashboard Screenshot Board captured")
    print(f"Target: {(ROOT / 'audit_outputs/dashboard-access/latest-url.masked.txt').read_text().strip() if (ROOT / 'audit_outputs/dashboard-access/latest-url.masked.txt').exists() else target}")
    print(f"Board file: {board}")

    if not args.capture_only:
      serve()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

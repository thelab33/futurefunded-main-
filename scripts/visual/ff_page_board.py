#!/usr/bin/env python3
"""
FutureFunded shared screenshot board engine.

Creates a real screenshot board for one page using Playwright:
- Desktop PNG
- Tablet PNG
- Mobile PNG

Used by:
- ff-homepage-board.py
- ff-campaign-board.py
- ff-onboarding-board.py
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "audit_outputs" / "visual-boards"


def find_free_port(preferred: int) -> int:
    for port in range(preferred, preferred + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free local board port found.")


def check_url(url: str) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FutureFundedBoard/1.0"})
        with urllib.request.urlopen(req, timeout=8) as res:
            return 200 <= res.status < 400, f"{res.status} {res.reason}"
    except Exception as exc:
        return False, str(exc)


def run_capture(base: str, path: str, out_dir: Path, stamp: str, wait_ms: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    capture_js = out_dir / "capture-page.mjs"
    capture_js.write_text(
        """
import { chromium } from "playwright";
import path from "node:path";

const base = process.argv[2];
const pagePath = process.argv[3];
const outDir = process.argv[4];
const stamp = process.argv[5];
const waitMs = Number(process.argv[6] || 900);

const target = `${base.replace(/\\/$/, "")}${pagePath}`;
const joiner = target.includes("?") ? "&" : "?";

const viewports = [
  { name: "desktop", width: 1440, height: 1200 },
  { name: "tablet", width: 834, height: 1200 },
  { name: "mobile", width: 390, height: 1280 },
];

const browser = await chromium.launch({ headless: true });

for (const vp of viewports) {
  const page = await browser.newPage({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: 1,
  });

  await page.goto(`${target}${joiner}board=${stamp}&viewport=${vp.name}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });

  await page.waitForTimeout(waitMs);

  await page.screenshot({
    path: path.join(outDir, `${vp.name}.png`),
    fullPage: true,
  });

  await page.close();
}

await browser.close();
""".strip(),
        encoding="utf-8",
    )

    node = shutil.which("node")
    if not node:
        raise SystemExit("❌ Node is not available. Install/use Node first.")

    result = subprocess.run(
        [node, str(capture_js), base, path, str(out_dir), stamp, str(wait_ms)],
        cwd=str(ROOT),
        text=True,
    )

    if result.returncode != 0:
        raise SystemExit(
            "❌ Playwright capture failed.\n\n"
            "Try:\n"
            "  npm install -D playwright\n"
            "  npx playwright install chromium\n\n"
            "Then rerun the board command."
        )


def write_board(
    *,
    title: str,
    slug: str,
    base: str,
    page_path: str,
    out_dir: Path,
    stamp: str,
) -> Path:
    target = f"{base.rstrip('/')}{page_path}"
    board_name = f"{slug}-board.html"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #130904;
      --panel: rgba(255, 249, 239, .96);
      --ink: #26140b;
      --muted: rgba(38, 20, 11, .62);
      --line: rgba(255, 255, 255, .18);
      --orange: #ff5a1f;
      --shell: min(100% - 24px, 1760px);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background:
        radial-gradient(circle at 10% -10%, rgba(255, 90, 31, .26), transparent 34rem),
        radial-gradient(circle at 90% 0%, rgba(15, 118, 110, .18), transparent 30rem),
        linear-gradient(145deg, #211007, var(--bg));
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      border-bottom: 1px solid var(--line);
      background: rgba(19, 9, 4, .84);
      color: white;
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
    }}

    .topbar {{
      width: var(--shell);
      min-height: 68px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(1.05rem, 1.8vw, 1.35rem);
      letter-spacing: -.04em;
    }}

    .meta {{
      margin-top: 3px;
      color: rgba(255,255,255,.68);
      font-size: .82rem;
      font-weight: 750;
    }}

    .actions {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }}

    a {{
      color: inherit;
      text-decoration: none;
    }}

    .pill {{
      min-height: 34px;
      padding: 0 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      background: rgba(255,255,255,.10);
      color: white;
      font-size: .82rem;
      font-weight: 900;
      white-space: nowrap;
    }}

    .pill.primary {{
      background: linear-gradient(135deg, var(--orange), #f97316);
      box-shadow: 0 12px 26px rgba(255, 90, 31, .26);
    }}

    main {{
      width: var(--shell);
      margin: 0 auto;
      padding: 18px 0 42px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: minmax(720px, 1fr) minmax(420px, .55fr);
      gap: 18px;
      align-items: start;
    }}

    .stack {{
      display: grid;
      gap: 18px;
    }}

    .card {{
      overflow: hidden;
      border: 1px solid rgba(255,255,255,.2);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: 0 24px 80px rgba(0,0,0,.26);
    }}

    .cardHead {{
      min-height: 54px;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      border-bottom: 1px solid rgba(38, 20, 11, .10);
      background:
        radial-gradient(circle at 0 0, rgba(255, 90, 31, .12), transparent 18rem),
        rgba(255,255,255,.78);
    }}

    .cardHead strong {{
      display: block;
      font-size: .94rem;
      letter-spacing: -.02em;
    }}

    .cardHead span {{
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: .76rem;
      font-weight: 850;
    }}

    .viewport {{
      overflow: auto;
      background: #f2dfc4;
    }}

    .desktop .viewport {{
      max-height: 900px;
    }}

    .tablet .viewport,
    .mobile .viewport {{
      max-height: 760px;
    }}

    img {{
      display: block;
      height: auto;
      background: #f2dfc4;
    }}

    .desktop img {{
      width: 100%;
      min-width: 960px;
    }}

    .tablet img {{
      width: 834px;
      max-width: none;
    }}

    .mobile img {{
      width: 390px;
      max-width: none;
    }}

    .shotWrap {{
      width: fit-content;
      margin: 0 auto;
    }}

    @media (max-width: 1250px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 720px) {{
      .topbar {{
        min-height: 0;
        padding: 13px 0;
        align-items: flex-start;
        flex-direction: column;
      }}

      .actions {{
        justify-content: flex-start;
      }}

      main {{
        width: min(100% - 12px, 1760px);
      }}

      .desktop img {{
        min-width: 720px;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>{title}</h1>
        <div class="meta">Captured target: {target}</div>
      </div>
      <div class="actions">
        <a class="pill primary" href="{target}" target="_blank" rel="noreferrer">Open page</a>
        <a class="pill" href="./desktop.png?{stamp}" target="_blank" rel="noreferrer">Desktop PNG</a>
        <a class="pill" href="./tablet.png?{stamp}" target="_blank" rel="noreferrer">Tablet PNG</a>
        <a class="pill" href="./mobile.png?{stamp}" target="_blank" rel="noreferrer">Mobile PNG</a>
      </div>
    </div>
  </header>

  <main>
    <div class="grid">
      <section class="card desktop">
        <div class="cardHead">
          <div><strong>Desktop</strong><span>1440px screenshot</span></div>
          <a class="pill primary" href="./desktop.png?{stamp}" target="_blank" rel="noreferrer">Open</a>
        </div>
        <div class="viewport">
          <div class="shotWrap">
            <img src="./desktop.png?{stamp}" alt="Desktop screenshot">
          </div>
        </div>
      </section>

      <div class="stack">
        <section class="card tablet">
          <div class="cardHead">
            <div><strong>Tablet</strong><span>834px screenshot</span></div>
            <a class="pill primary" href="./tablet.png?{stamp}" target="_blank" rel="noreferrer">Open</a>
          </div>
          <div class="viewport">
            <div class="shotWrap">
              <img src="./tablet.png?{stamp}" alt="Tablet screenshot">
            </div>
          </div>
        </section>

        <section class="card mobile">
          <div class="cardHead">
            <div><strong>Mobile</strong><span>390px screenshot</span></div>
            <a class="pill primary" href="./mobile.png?{stamp}" target="_blank" rel="noreferrer">Open</a>
          </div>
          <div class="viewport">
            <div class="shotWrap">
              <img src="./mobile.png?{stamp}" alt="Mobile screenshot">
            </div>
          </div>
        </section>
      </div>
    </div>
  </main>
</body>
</html>
"""
    path_out = out_dir / board_name
    path_out.write_text(html, encoding="utf-8")
    return path_out


def run_page_board(
    *,
    default_slug: str,
    default_title: str,
    default_path: str,
    default_port: int,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("FF_BOARD_BASE", "http://127.0.0.1:5000"))
    parser.add_argument("--path", default=os.environ.get("FF_BOARD_PATH", default_path))
    parser.add_argument("--slug", default=default_slug)
    parser.add_argument("--title", default=default_title)
    parser.add_argument("--port", type=int, default=int(os.environ.get("FF_BOARD_PORT", str(default_port))))
    parser.add_argument("--wait", type=int, default=int(os.environ.get("FF_BOARD_WAIT_MS", "900")))
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--capture-only", action="store_true", help="Capture screenshots and write board HTML, but do not start the board server.")
    parser.add_argument("--allow-unreachable", action="store_true", help="Attempt capture even if the target URL check fails.")
    args = parser.parse_args()

    slug = args.slug.strip().replace(" ", "-").lower()
    out_dir = OUT_ROOT / slug
    target = f"{args.base.rstrip('/')}{args.path}"

    ok, status = check_url(target)
    if not ok:
        print(f"⚠️ Target not confirmed live: {target}")
        print(f"   {status}")
        print("   Start the app first: ffserver restart")
        print()

    stamp = str(int(time.time()))
    run_capture(args.base, args.path, out_dir, stamp, args.wait)
    board_file = write_board(
        title=args.title,
        slug=slug,
        base=args.base,
        page_path=args.path,
        out_dir=out_dir,
        stamp=stamp,
    )

    if args.capture_only:
        print(f"✅ {args.title} captured")
        print(f"Target: {target}")
        print(f"Board file: {board_file}")
        return 0

    port = find_free_port(args.port)
    os.chdir(str(out_dir))

    url = f"http://127.0.0.1:{port}/{board_file.name}"

    print(f"✅ {args.title} ready")
    print(f"Target: {target}")
    print(f"Board:  {url}")
    print("Press Ctrl+C to stop.")
    print()

    if not args.no_open:
        webbrowser.open(url)

    server = ThreadingHTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\nStopped {args.title}.")
        return 0


if __name__ == "__main__":
    raise SystemExit(
        run_page_board(
            default_slug="page",
            default_title="FutureFunded Page Screenshot Board",
            default_path="/",
            default_port=8765,
        )
    )

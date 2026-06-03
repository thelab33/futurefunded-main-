#!/usr/bin/env python3
"""
FutureFunded all-page screenshot board index.

Captures the major FutureFunded surfaces into separate board folders, then
opens one master visual QA board.

Pages:
- Public homepage / redirect surface
- Platform product home
- Campaign page
- Onboarding
- Login
- Dashboard
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "audit_outputs" / "visual-boards"

PAGES = [
    {
        "label": "Public Home",
        "slug": "homepage",
        "script": "scripts/visual/ff-homepage-board.py",
        "desc": "Root public entry surface.",
    },
    {
        "label": "Platform Home",
        "slug": "platform-home",
        "script": "scripts/visual/ff-platform-home-board.py",
        "desc": "Warm premium product homepage.",
    },
    {
        "label": "Campaign Page",
        "slug": "campaign",
        "script": "scripts/visual/ff-campaign-board.py",
        "desc": "Public donor and sponsor campaign page.",
    },
    {
        "label": "Onboarding",
        "slug": "onboarding",
        "script": "scripts/visual/ff-onboarding-board.py",
        "desc": "Compact campaign setup workflow.",
    },
    {
        "label": "Login",
        "slug": "platform-login",
        "script": "scripts/visual/ff-platform-login-board.py",
        "desc": "Organizer access page.",
    },
    {
        "label": "Dashboard",
        "slug": "platform-dashboard",
        "script": "scripts/visual/ff-platform-dashboard-board.py",
        "desc": "Operator command center.",
    },
]


def find_free_port(preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free local board port found.")


def run_capture(page: dict[str, str]) -> int:
    script = ROOT / page["script"]

    if not script.exists():
        print(f"❌ Missing board script: {page['script']}")
        return 1

    print(f"== Capture: {page['label']} ==")
    result = subprocess.run(
        [sys.executable, str(script), "--capture-only"],
        cwd=str(ROOT),
        text=True,
    )
    print()
    return int(result.returncode)


def write_index(stamp: str) -> Path:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    cards: list[str] = []

    for page in PAGES:
        slug = page["slug"]
        board = f"./{slug}/{slug}-board.html"
        desktop = f"./{slug}/desktop.png?{stamp}"
        tablet = f"./{slug}/tablet.png?{stamp}"
        mobile = f"./{slug}/mobile.png?{stamp}"

        cards.append(f"""
        <article class="ffBoardCard">
          <div class="ffBoardCard__head">
            <div>
              <p>{page["label"]}</p>
              <h2>{page["desc"]}</h2>
            </div>
            <a class="ffBoardPill ffBoardPill--hot" href="{board}" target="_blank" rel="noreferrer">Open board</a>
          </div>

          <a class="ffBoardShot" href="{board}" target="_blank" rel="noreferrer">
            <img src="{desktop}" alt="{page["label"]} desktop screenshot">
          </a>

          <div class="ffBoardLinks">
            <a href="{desktop}" target="_blank" rel="noreferrer">Desktop</a>
            <a href="{tablet}" target="_blank" rel="noreferrer">Tablet</a>
            <a href="{mobile}" target="_blank" rel="noreferrer">Mobile</a>
          </div>
        </article>
        """)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FutureFunded All Page Screenshot Boards</title>
  <style>
    :root {{
      --bg: #130904;
      --panel: rgba(255, 249, 239, .96);
      --ink: #26140b;
      --muted: rgba(255,255,255,.68);
      --line: rgba(255,255,255,.18);
      --orange: #ff5a1f;
      --shell: min(100% - 28px, 1540px);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background:
        radial-gradient(circle at 8% -10%, rgba(255,90,31,.32), transparent 34rem),
        radial-gradient(circle at 92% 0%, rgba(15,118,110,.18), transparent 30rem),
        linear-gradient(145deg, #211007, var(--bg));
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      color: white;
      background: rgba(19,9,4,.86);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
    }}

    .ffBoardTopbar {{
      width: var(--shell);
      min-height: 72px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(1.1rem, 2vw, 1.55rem);
      letter-spacing: -.045em;
    }}

    .ffBoardMeta {{
      margin-top: 4px;
      color: var(--muted);
      font-size: .84rem;
      font-weight: 800;
    }}

    main {{
      width: var(--shell);
      margin: 0 auto;
      padding: 22px 0 48px;
    }}

    .ffBoardGrid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      align-items: start;
    }}

    .ffBoardCard {{
      overflow: hidden;
      border: 1px solid rgba(255,255,255,.2);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: 0 24px 80px rgba(0,0,0,.26);
    }}

    .ffBoardCard__head {{
      min-height: 76px;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      border-bottom: 1px solid rgba(38,20,11,.1);
      background:
        radial-gradient(circle at 0 0, rgba(255,90,31,.12), transparent 18rem),
        rgba(255,255,255,.78);
    }}

    .ffBoardCard__head p {{
      margin: 0 0 4px;
      color: #b94717;
      font-size: .7rem;
      font-weight: 950;
      letter-spacing: .14em;
      text-transform: uppercase;
    }}

    .ffBoardCard__head h2 {{
      margin: 0;
      font-size: 1rem;
      letter-spacing: -.03em;
      line-height: 1.05;
    }}

    a {{
      color: inherit;
      text-decoration: none;
    }}

    .ffBoardPill {{
      min-height: 34px;
      padding: 0 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      color: white;
      background: rgba(255,255,255,.1);
      font-size: .82rem;
      font-weight: 950;
      white-space: nowrap;
    }}

    .ffBoardPill--hot {{
      background: linear-gradient(135deg, var(--orange), #f97316);
      box-shadow: 0 12px 26px rgba(255,90,31,.26);
    }}

    .ffBoardShot {{
      display: block;
      max-height: 560px;
      overflow: auto;
      background: #f2dfc4;
    }}

    .ffBoardShot img {{
      display: block;
      width: 100%;
      min-width: 720px;
      height: auto;
      background: #f2dfc4;
    }}

    .ffBoardLinks {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 12px 14px 14px;
      border-top: 1px solid rgba(38,20,11,.1);
    }}

    .ffBoardLinks a {{
      min-height: 32px;
      display: inline-flex;
      align-items: center;
      padding: 0 11px;
      border-radius: 999px;
      background: rgba(255,255,255,.82);
      border: 1px solid rgba(38,20,11,.1);
      font-size: .78rem;
      font-weight: 950;
    }}

    @media (max-width: 980px) {{
      .ffBoardGrid {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 720px) {{
      .ffBoardTopbar {{
        min-height: 0;
        padding: 14px 0;
        align-items: flex-start;
        flex-direction: column;
      }}

      main {{
        width: min(100% - 12px, 1540px);
      }}

      .ffBoardCard__head {{
        align-items: flex-start;
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="ffBoardTopbar">
      <div>
        <h1>FutureFunded All Page Screenshot Boards</h1>
        <div class="ffBoardMeta">Desktop / tablet / mobile proof for every flagship page</div>
      </div>
      <div class="ffBoardMeta">Generated {stamp}</div>
    </div>
  </header>

  <main>
    <div class="ffBoardGrid">
      {''.join(cards)}
    </div>
  </main>
</body>
</html>
"""

    path = OUT_ROOT / "all-page-boards.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> int:
    failures: list[str] = []

    for page in PAGES:
        code = run_capture(page)
        if code != 0:
            failures.append(page["label"])

    if failures:
        print("❌ Some page boards failed:")
        for item in failures:
            print(f"  - {item}")
        print()
        print("Run `ffserver restart`, wait for route smoke, then rerun.")
        return 1

    stamp = str(int(time.time()))
    index = write_index(stamp)

    port = find_free_port(8788)
    os.chdir(str(OUT_ROOT))

    url = f"http://127.0.0.1:{port}/{index.name}"

    print("✅ FutureFunded all-page board index ready")
    print(f"Board: {url}")
    print("Press Ctrl+C to stop.")
    print()

    webbrowser.open(url)

    server = ThreadingHTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped all-page board index.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

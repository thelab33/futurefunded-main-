#!/usr/bin/env python3
"""
FutureFunded platform master screenshot board.

Captures the main platform pages into separate board folders, then opens
one index page linking all of them.

Pages:
- Platform home
- Onboarding
- Login
- Dashboard
"""

from __future__ import annotations

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
        "label": "Platform Home",
        "slug": "platform-home",
        "script": "scripts/visual/ff-platform-home-board.py",
        "desc": "Main platform landing/workspace route.",
    },
    {
        "label": "Onboarding",
        "slug": "onboarding",
        "script": "scripts/visual/ff-onboarding-board.py",
        "desc": "Compact campaign setup flow.",
    },
    {
        "label": "Login",
        "slug": "platform-login",
        "script": "scripts/visual/ff-platform-login-board.py",
        "desc": "Operator/auth entry page.",
    },
    {
        "label": "Dashboard",
        "slug": "platform-dashboard",
        "script": "scripts/visual/ff-platform-dashboard-board.py",
        "desc": "Operator dashboard using the local dev access token.",
    },
]


def find_free_port(preferred: int) -> int:
    for port in range(preferred, preferred + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free local board port found.")


def run_capture(script: str) -> int:
    print(f"== Capture: {script} ==")
    result = subprocess.run(
        [sys.executable, script, "--capture-only"],
        cwd=str(ROOT),
        text=True,
    )
    print()
    return int(result.returncode)


def write_index(stamp: str) -> Path:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    cards = []
    for page in PAGES:
        slug = page["slug"]
        board = f"./{slug}/{slug}-board.html"
        desktop = f"./{slug}/desktop.png?{stamp}"
        tablet = f"./{slug}/tablet.png?{stamp}"
        mobile = f"./{slug}/mobile.png?{stamp}"

        cards.append(f"""
        <article class="card">
          <div class="cardHead">
            <div>
              <h2>{page["label"]}</h2>
              <p>{page["desc"]}</p>
            </div>
            <a class="pill primary" href="{board}" target="_blank" rel="noreferrer">Open board</a>
          </div>

          <a class="shot" href="{board}" target="_blank" rel="noreferrer">
            <img src="{desktop}" alt="{page["label"]} desktop screenshot">
          </a>

          <div class="links">
            <a href="{desktop}" target="_blank" rel="noreferrer">Desktop PNG</a>
            <a href="{tablet}" target="_blank" rel="noreferrer">Tablet PNG</a>
            <a href="{mobile}" target="_blank" rel="noreferrer">Mobile PNG</a>
          </div>
        </article>
        """)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FutureFunded Platform Screenshot Boards</title>
  <style>
    :root {{
      --bg: #130904;
      --panel: rgba(255, 249, 239, .96);
      --ink: #26140b;
      --muted: rgba(38, 20, 11, .64);
      --line: rgba(255, 255, 255, .18);
      --orange: #ff5a1f;
      --shell: min(100% - 28px, 1480px);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background:
        radial-gradient(circle at 10% -10%, rgba(255, 90, 31, .28), transparent 34rem),
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
      color: #fff;
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
    }}

    .topbar {{
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

    .meta {{
      margin-top: 4px;
      color: rgba(255,255,255,.68);
      font-size: .86rem;
      font-weight: 750;
    }}

    main {{
      width: var(--shell);
      margin: 0 auto;
      padding: 22px 0 48px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      align-items: start;
    }}

    .card {{
      overflow: hidden;
      border: 1px solid rgba(255,255,255,.2);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: 0 24px 80px rgba(0,0,0,.26);
    }}

    .cardHead {{
      min-height: 70px;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      border-bottom: 1px solid rgba(38, 20, 11, .10);
      background:
        radial-gradient(circle at 0 0, rgba(255, 90, 31, .12), transparent 18rem),
        rgba(255,255,255,.78);
    }}

    h2 {{
      margin: 0;
      font-size: 1rem;
      letter-spacing: -.03em;
    }}

    p {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: .82rem;
      font-weight: 760;
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
      color: white;
      background: rgba(255,255,255,.10);
      font-size: .82rem;
      font-weight: 900;
      white-space: nowrap;
    }}

    .pill.primary {{
      background: linear-gradient(135deg, var(--orange), #f97316);
      box-shadow: 0 12px 26px rgba(255, 90, 31, .26);
    }}

    .shot {{
      display: block;
      max-height: 520px;
      overflow: auto;
      background: #f2dfc4;
    }}

    .shot img {{
      display: block;
      width: 100%;
      min-width: 720px;
      height: auto;
    }}

    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 12px 14px 14px;
      border-top: 1px solid rgba(38, 20, 11, .10);
    }}

    .links a {{
      min-height: 32px;
      display: inline-flex;
      align-items: center;
      padding: 0 11px;
      border-radius: 999px;
      color: var(--ink);
      background: rgba(255,255,255,.82);
      border: 1px solid rgba(38,20,11,.1);
      font-size: .78rem;
      font-weight: 900;
    }}

    @media (max-width: 980px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 720px) {{
      .topbar {{
        min-height: 0;
        padding: 14px 0;
        align-items: flex-start;
        flex-direction: column;
      }}

      main {{
        width: min(100% - 12px, 1480px);
      }}

      .cardHead {{
        align-items: flex-start;
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>FutureFunded Platform Screenshot Boards</h1>
        <div class="meta">Separate visual QA boards for main platform pages</div>
      </div>
      <div class="meta">Generated {stamp}</div>
    </div>
  </header>

  <main>
    <div class="grid">
      {''.join(cards)}
    </div>
  </main>
</body>
</html>
"""

    path = OUT_ROOT / "platform-main-boards.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> int:
    failures = []
    for page in PAGES:
        code = run_capture(page["script"])
        if code != 0:
            failures.append(page["label"])

    if failures:
        print("❌ Some platform boards failed:")
        for item in failures:
            print(f"  - {item}")
        print()
        print("Most common cause: Flask is not running. Run `ffserver restart` and wait for route smoke to finish.")
        return 1

    stamp = str(int(time.time()))
    index = write_index(stamp)

    port = find_free_port(8779)
    url = f"http://127.0.0.1:{port}/{index.name}"

    print("✅ FutureFunded platform board index ready")
    print(f"Board: {url}")
    print("Press Ctrl+C to stop.")
    print()

    webbrowser.open(url)

    import os
    os.chdir(str(OUT_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nStopped platform board index.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

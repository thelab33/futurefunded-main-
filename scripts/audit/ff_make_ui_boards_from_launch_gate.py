#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

SRC = Path("audit_outputs/visual-launch-gate/latest")
SRC_SHOTS = SRC / "screenshots"
REPORT = SRC / "report.json"

OUT = Path("audit_outputs/page-ui-board/latest")
OUT.mkdir(parents=True, exist_ok=True)

if not REPORT.exists():
    raise SystemExit(f"Missing {REPORT}. Run scripts/release/ff_visual_launch_gate.mjs first.")
if not SRC_SHOTS.exists():
    raise SystemExit(f"Missing {SRC_SHOTS}. Run scripts/release/ff_visual_launch_gate.mjs first.")

report = json.loads(REPORT.read_text(encoding="utf-8"))
results = report.get("results", [])

# Clean board output, but keep directory.
for item in OUT.iterdir():
    if item.is_file():
        item.unlink()
    elif item.is_dir():
        shutil.rmtree(item)

for shot in SRC_SHOTS.glob("*.png"):
    shutil.copy2(shot, OUT / shot.name)

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)

def rel_shot(path_value) -> str:
    if not path_value:
        return ""
    return Path(str(path_value)).name

def surface_priority(surface: str) -> str:
    if surface == "Campaign page":
        return "Flagship donor product"
    if surface == "Platform homepage":
        return "Enterprise SaaS surface"
    if "Dashboard token" in surface or surface == "Dashboard token":
        return "Operator command center"
    if surface == "Launch onboarding":
        return "Launch workspace"
    if surface == "Operator login":
        return "Trust gate"
    if surface == "Dashboard locked":
        return "Private-data gate"
    return "Review"

CSS = """
:root {
  --bg: #f5efe7;
  --panel: rgba(255,255,255,.88);
  --ink: #17120e;
  --muted: rgba(23,18,14,.68);
  --line: rgba(70,45,24,.14);
  --brand: #f35f16;
  --good: #0f766e;
  --bad: #b42318;
  --shadow: 0 18px 60px rgba(52,33,17,.12);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background:
    radial-gradient(circle at 10% 0%, rgba(243,95,22,.16), transparent 34rem),
    linear-gradient(180deg, #fff8ef, var(--bg));
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
header {
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--line);
  background: rgba(255,248,239,.92);
  backdrop-filter: blur(16px);
  padding: 18px clamp(16px, 4vw, 44px);
}
header h1 {
  margin: 0;
  font-size: clamp(1.75rem, 4vw, 3rem);
  letter-spacing: -.06em;
  line-height: .95;
}
header p {
  max-width: 86ch;
  margin: 8px 0 0;
  color: var(--muted);
  font-size: .98rem;
  line-height: 1.45;
}
.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}
.nav a {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255,255,255,.74);
  color: var(--ink);
  font-size: .82rem;
  font-weight: 850;
  padding: 0 14px;
  text-decoration: none;
}
main {
  width: min(100% - 28px, var(--board-width, 1500px));
  margin: 0 auto;
  padding: 26px 0 70px;
}
.board {
  display: grid;
  grid-template-columns: var(--board-columns, repeat(2, minmax(0, 1fr)));
  gap: 22px;
}
article {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 26px;
  background: var(--panel);
  box-shadow: var(--shadow);
}
.cardHead {
  display: grid;
  gap: 8px;
  padding: 16px 16px 14px;
  border-bottom: 1px solid var(--line);
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
}
.pill {
  display: inline-flex;
  min-height: 26px;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 9px;
  color: var(--muted);
  font-size: .74rem;
  font-weight: 850;
}
.pill.ok { color: var(--good); border-color: rgba(15,118,110,.22); background: rgba(15,118,110,.06); }
.pill.bad { color: var(--bad); border-color: rgba(180,35,24,.22); background: rgba(180,35,24,.06); }
.pill.hot { color: #a84310; border-color: rgba(243,95,22,.25); background: rgba(243,95,22,.08); }
h2 {
  margin: 0;
  font-size: 1.04rem;
  letter-spacing: -.035em;
  line-height: 1.05;
}
.note, .url, .h1 {
  color: var(--muted);
  font-size: .78rem;
  line-height: 1.35;
}
.url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.imgWrap {
  display: block;
  background: #fff;
}
img {
  display: block;
  width: 100%;
  height: auto;
  max-height: none;
  object-fit: contain;
  object-position: top center;
  border: 0;
}
details {
  padding: 12px 16px 16px;
  border-top: 1px solid var(--line);
}
summary {
  cursor: pointer;
  color: var(--muted);
  font-size: .78rem;
  font-weight: 850;
}
pre {
  overflow: auto;
  max-height: 260px;
  margin: 12px 0 0;
  border-radius: 14px;
  background: rgba(23,18,14,.06);
  padding: 12px;
  color: rgba(23,18,14,.78);
  font-size: .72rem;
  line-height: 1.45;
}
.launcher {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.launcher a {
  display: grid;
  gap: 10px;
  min-height: 190px;
  align-content: end;
  border: 1px solid var(--line);
  border-radius: 28px;
  background: var(--panel);
  box-shadow: var(--shadow);
  color: var(--ink);
  padding: 22px;
  text-decoration: none;
}
.launcher strong {
  font-size: clamp(1.5rem, 4vw, 2.4rem);
  letter-spacing: -.06em;
  line-height: .95;
}
.launcher span {
  color: var(--muted);
  line-height: 1.45;
}
@media (max-width: 980px) {
  .board, .launcher { grid-template-columns: 1fr; }
}
"""

def card(r: dict) -> str:
    shot = rel_shot(r.get("screenshot"))
    if not shot:
        safe = r.get("surface", "").lower().replace(" ", "-")
        shot = f"{safe}-{r.get('viewport')}.png"
    ok = bool(r.get("ok"))
    payload = {
        "status": r.get("status"),
        "h1Count": r.get("h1Count"),
        "ctaCount": r.get("ctaCount"),
        "overflowX": r.get("overflowX"),
        "bodyTextLength": r.get("bodyTextLength"),
        "errors": r.get("errors") or r.get("error"),
    }
    return f"""
<article>
  <div class="cardHead">
    <div class="meta">
      <span class="pill {'ok' if ok else 'bad'}">{'PASS' if ok else 'CHECK'}</span>
      <span class="pill hot">{esc(surface_priority(r.get('surface', '')))}</span>
      <span class="pill">{esc(r.get('viewport'))}</span>
      <span class="pill">HTTP {esc(r.get('status'))}</span>
    </div>
    <h2>{esc(r.get('surface'))}</h2>
    <div class="note">Official launch-gate screenshot. No extra Playwright board capture.</div>
    <div class="url">{esc(r.get('url', ''))}</div>
  </div>
  <a class="imgWrap" href="./{esc(shot)}" target="_blank" rel="noreferrer">
    <img src="./{esc(shot)}" alt="{esc(r.get('surface'))} {esc(r.get('viewport'))} screenshot">
  </a>
  <details>
    <summary>Audit details</summary>
    <pre>{esc(json.dumps(payload, indent=2))}</pre>
  </details>
</article>
"""

def board(kind: str, title: str, description: str, width: str, columns: str, height: str) -> str:
    subset = [r for r in results if r.get("viewport") == kind]
    pass_count = sum(1 for r in subset if r.get("ok"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{esc(title)}</title>
  <style>{CSS}</style>
</head>
<body style="--board-width:{esc(width)};--board-columns:{esc(columns)};--preview-height:{esc(height)};">
  <header>
    <h1>{esc(title)}</h1>
    <p>{esc(description)} Generated from the official visual launch gate. Passing: {pass_count}/{len(subset)}.</p>
    <nav class="nav" aria-label="Review board navigation">
      <a href="./index.html">Board home</a>
      <a href="./desktop.html">Desktop board</a>
      <a href="./mobile.html">Mobile board</a>
    </nav>
  </header>
  <main>
    <section class="board">
      {''.join(card(r) for r in subset)}
    </section>
  </main>
</body>
</html>"""

index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FutureFunded UI Review Boards</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <h1>FutureFunded UI Review Boards</h1>
    <p>These boards are generated from the official visual launch gate screenshots, so they cannot freeze on extra browser capture.</p>
  </header>
  <main>
    <section class="launcher">
      <a href="./desktop.html"><strong>Desktop board</strong><span>Review enterprise hierarchy, campaign trust, dashboard polish, and spacing.</span></a>
      <a href="./mobile.html"><strong>Mobile board</strong><span>Review donor/family experience, CTA clarity, density, and launch-day confidence.</span></a>
    </section>
  </main>
</body>
</html>"""

(OUT / "index.html").write_text(index, encoding="utf-8")
(OUT / "desktop.html").write_text(board("desktop", "FutureFunded Desktop UI Review Board", "Desktop-only board for layout, hierarchy, spacing, and premium polish.", "1560px", "repeat(2, minmax(0, 1fr))", "620px"), encoding="utf-8")
(OUT / "mobile.html").write_text(board("mobile", "FutureFunded Mobile UI Review Board", "Mobile-only board for donor trust, CTA clarity, and launch-day usability.", "980px", "repeat(2, minmax(0, 1fr))", "720px"), encoding="utf-8")

print("FutureFunded launch-gate boards complete")
print(f"Open: {OUT / 'index.html'}")
print("Serve with: python -m http.server 8765 -d audit_outputs/page-ui-board/latest")

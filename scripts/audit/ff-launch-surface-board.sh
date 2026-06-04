#!/usr/bin/env bash
set -euo pipefail

BASE="${FF_BASE_URL:-http://127.0.0.1:5000}"
STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/launch-surface-board-${STAMP}"

mkdir -p "$OUT/screenshots" "$OUT/rendered"

echo "== FutureFunded canonical launch surface board =="
echo "OUT=$OUT"

echo
echo "== Ensure server =="
if ! curl -fsS "$BASE/healthz" >/dev/null; then
  ffserver restart
fi

echo
echo "== Resolve dashboard token without printing it =="
TOKEN=""
if [ -s /tmp/ff_operator_token ]; then
  TOKEN="$(tr -d '\r\n\t ' < /tmp/ff_operator_token)"
fi

if [ -z "$TOKEN" ] && [ -f .env.local ]; then
  TOKEN="$(
    { grep -E '^[[:space:]]*FF_OPERATOR_ACCESS_TOKEN=' .env.local 2>/dev/null || true; } \
      | tail -n 1 \
      | sed -E 's/^[[:space:]]*FF_OPERATOR_ACCESS_TOKEN=//' \
      | sed -E 's/^["'\''"]|["'\''"]$//g' \
      | tr -d '\r\n'
  )"
fi

if [ -z "$TOKEN" ]; then
  echo "❌ Missing private dashboard token."
  echo "Expected /tmp/ff_operator_token or .env.local FF_OPERATOR_ACCESS_TOKEN."
  exit 1
fi

echo "token_length=${#TOKEN}" > "$OUT/dashboard-token-proof.txt"

echo
echo "== Route map =="
python - <<'PY' > "$OUT/flask-routes.csv"
import csv

rows = []
try:
    from apps.web.app import create_app
    app = create_app()
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
        rows.append({
            "rule": str(rule),
            "endpoint": rule.endpoint,
            "methods": " ".join(sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})),
            "arguments": ",".join(sorted(rule.arguments)),
        })
except Exception as exc:
    rows.append({
        "rule": "ERROR",
        "endpoint": type(exc).__name__,
        "methods": str(exc),
        "arguments": "",
    })

w = csv.DictWriter(open("/dev/stdout", "w", newline=""), fieldnames=["rule", "endpoint", "methods", "arguments"])
w.writeheader()
w.writerows(rows)
PY

echo
echo "== Canonical surface fetch proof =="
TOKEN="$TOKEN" BASE="$BASE" OUT="$OUT" STAMP="$STAMP" python - <<'PY'
from pathlib import Path
from urllib.parse import urlencode
import csv
import hashlib
import os
import re
import subprocess

base = os.environ["BASE"].rstrip("/")
token = os.environ["TOKEN"]
out = Path(os.environ["OUT"])
stamp = os.environ["STAMP"]

surfaces = [
    {
        "id": "home",
        "label": "Homepage",
        "path": "/",
        "expected_page": "platform",
        "kind": "canonical",
        "notes": "Root public entry surface",
    },
    {
        "id": "platform_alias",
        "label": "Platform home alias",
        "path": "/platform/",
        "expected_page": "platform",
        "kind": "alias",
        "notes": "Alias check only; do not show as a second homepage",
    },
    {
        "id": "campaign",
        "label": "Campaign",
        "path": "/c/connect-atx-elite",
        "expected_page": "campaign",
        "kind": "canonical",
        "notes": "Public donor and sponsor campaign page",
    },
    {
        "id": "onboarding",
        "label": "Onboarding",
        "path": "/platform/onboarding",
        "expected_page": "platform-onboarding",
        "kind": "canonical",
        "notes": "Campaign setup workflow",
    },
    {
        "id": "dashboard",
        "label": "Private Dashboard",
        "path": f"/platform/dashboard?{urlencode({'access_token': token})}",
        "masked_path": "/platform/dashboard?access_token=***MASKED***",
        "expected_page": "platform-dashboard",
        "kind": "canonical",
        "notes": "Private operator command center",
    },
    {
        "id": "login_support",
        "label": "Login support route",
        "path": "/platform/login",
        "expected_page": "platform-login",
        "kind": "support",
        "notes": "Security/access route; not a flagship board page",
    },
]

rows = []

def fetch(url, dest):
    cmd = ["curl", "-fsSL", "-o", str(dest), "-w", "%{http_code}\t%{content_type}\t%{size_download}", url]
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    parts = cp.stdout.strip().split("\t") if cp.stdout.strip() else ["000", "", "0"]
    return {
        "status": parts[0] if len(parts) > 0 else "000",
        "content_type": parts[1] if len(parts) > 1 else "",
        "bytes": parts[2] if len(parts) > 2 else "0",
        "curl_rc": cp.returncode,
        "stderr": cp.stderr.strip()[:220],
    }

for index, surface in enumerate(surfaces, 1):
    url = base + surface["path"]
    html_file = out / "rendered" / f"{index:02d}_{surface['id']}.html"
    result = fetch(url, html_file)
    html = html_file.read_text(errors="replace") if html_file.exists() else ""

    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    page = re.search(r'<html[^>]*data-ff-page=["\']([^"\']+)["\']', html, re.I)
    body = re.search(r'<body[^>]*class=["\']([^"\']+)["\']', html, re.I)

    normalized = re.sub(r"access_token=[^&\"'> ]+", "access_token=MASKED", html)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    html_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]

    actual_page = page.group(1) if page else ""
    expected_page = surface["expected_page"]
    ok = result["status"].startswith("2") and actual_page == expected_page

    rows.append({
        "id": surface["id"],
        "label": surface["label"],
        "kind": surface["kind"],
        "url_masked": base + surface.get("masked_path", surface["path"]),
        "status": result["status"],
        "expected_page": expected_page,
        "data_ff_page": actual_page,
        "title": " ".join(title.group(1).split()) if title else "",
        "body_class": body.group(1) if body else "",
        "bytes": result["bytes"],
        "html_hash": html_hash,
        "ok": "yes" if ok else "no",
        "notes": surface["notes"],
    })

with (out / "launch-surfaces.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

canonical_bad = [r for r in rows if r["kind"] == "canonical" and r["ok"] != "yes"]
if canonical_bad:
    print("❌ Canonical surface failure:")
    for r in canonical_bad:
        print(r)
    raise SystemExit(1)

for r in rows:
    print(f"{r['kind']:9s} {r['id']:16s} status={r['status']} page={r['data_ff_page']} ok={r['ok']} title={r['title']}")
PY

echo
echo "== Playwright availability =="
if ! node -e "require('playwright')" >/dev/null 2>&1; then
  echo "❌ Playwright missing."
  echo "Run: npm install -D playwright && npx playwright install chromium"
  exit 1
fi
echo "✅ Playwright available"

echo
echo "== Capture canonical launch screenshots only =="
TOKEN="$TOKEN" BASE="$BASE" OUT="$OUT" STAMP="$STAMP" node <<'NODE'
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const base = process.env.BASE.replace(/\/$/, "");
const token = process.env.TOKEN;
const out = process.env.OUT;
const stamp = process.env.STAMP;

const surfaces = [
  {
    id: "home",
    label: "Homepage",
    description: "Root public entry surface. /platform/ is treated as an alias, not another homepage.",
    url: `${base}/?launch_board=${stamp}`,
    expectedPage: "platform",
  },
  {
    id: "campaign",
    label: "Campaign",
    description: "Public donor and sponsor campaign page.",
    url: `${base}/c/connect-atx-elite?launch_board=${stamp}`,
    expectedPage: "campaign",
  },
  {
    id: "onboarding",
    label: "Onboarding",
    description: "Campaign setup workflow.",
    url: `${base}/platform/onboarding?launch_board=${stamp}`,
    expectedPage: "platform-onboarding",
  },
  {
    id: "dashboard",
    label: "Private Dashboard",
    description: "Private operator command center. Captured with local token; token is not embedded in this board.",
    url: `${base}/platform/dashboard?access_token=${encodeURIComponent(token)}&launch_board=${stamp}`,
    expectedPage: "platform-dashboard",
  },
];

const viewports = [
  { name: "desktop", label: "Desktop", width: 1440, height: 1500 },
  { name: "tablet", label: "Tablet", width: 834, height: 1300 },
  { name: "mobile", label: "Mobile", width: 390, height: 1200 },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const proof = [];

  for (const surface of surfaces) {
    for (const vp of viewports) {
      const page = await browser.newPage({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 1,
      });

      await page.goto(surface.url + `&viewport=${vp.name}`, {
        waitUntil: "networkidle",
        timeout: 60000,
      });

      const pageName = await page.locator("html").getAttribute("data-ff-page").catch(() => "");
      const title = await page.title();
      const html = await page.content();
      const hasLoginGate = html.includes("ff-loginAuthority") || title.includes("Organizer access");

      const ok = pageName === surface.expectedPage && !(surface.id === "dashboard" && hasLoginGate);
      proof.push(`${surface.id}/${vp.name}: page=${pageName} expected=${surface.expectedPage} ok=${ok} title=${title}`);

      if (!ok) {
        throw new Error(`Bad screenshot target: ${surface.id}/${vp.name} page=${pageName} title=${title}`);
      }

      await page.screenshot({
        path: path.join(out, "screenshots", `${surface.id}-${vp.name}.png`),
        fullPage: true,
        animations: "disabled",
      });

      await page.close();
    }
  }

  await browser.close();

  fs.writeFileSync(path.join(out, "screenshot-proof.txt"), proof.join("\n") + "\n");

  const esc = (value) => String(value).replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[m]));

  const cards = surfaces.map((surface) => {
    const links = viewports.map((vp) =>
      `<a href="screenshots/${surface.id}-${vp.name}.png" target="_blank" rel="noopener">${vp.label}</a>`
    ).join("");

    return `
      <section class="card">
        <header>
          <div>
            <p>${esc(surface.label)}</p>
            <h2>${esc(surface.description)}</h2>
          </div>
          <a class="open" href="screenshots/${surface.id}-desktop.png" target="_blank" rel="noopener">Open desktop</a>
        </header>
        <div class="shot">
          <img src="screenshots/${surface.id}-desktop.png" alt="${esc(surface.label)} desktop screenshot">
        </div>
        <nav>${links}</nav>
      </section>
    `;
  }).join("\n");

  const htmlDoc = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>FutureFunded Canonical Launch Surfaces</title>
  <style>
    :root {
      --bg: #1d0f08;
      --paper: rgba(255, 252, 246, .94);
      --ink: #201209;
      --muted: rgba(45, 29, 19, .68);
      --line: rgba(74, 45, 25, .14);
      --orange: #ff5a1f;
      --shadow: 0 24px 70px rgba(0, 0, 0, .24);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 0%, rgba(255,90,31,.22), transparent 28rem),
        radial-gradient(circle at 92% 8%, rgba(15,118,110,.12), transparent 28rem),
        linear-gradient(180deg, #251107 0%, var(--bg) 100%);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .wrap {
      width: min(100% - 28px, 1500px);
      margin: 0 auto;
      padding: 28px 0 46px;
    }

    .top {
      position: sticky;
      top: 12px;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 16px;
      margin-bottom: 22px;
      border: 1px solid rgba(255,255,255,.14);
      border-radius: 24px;
      color: #fff7ed;
      background: rgba(33, 18, 10, .86);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }

    .top h1 {
      margin: 0;
      font-size: clamp(1.15rem, 2vw, 1.75rem);
      line-height: .95;
      letter-spacing: -.055em;
    }

    .top p {
      margin: 4px 0 0;
      color: rgba(255,247,237,.72);
      font-size: .86rem;
      font-weight: 750;
    }

    .badge {
      border-radius: 999px;
      background: rgba(255,255,255,.1);
      padding: 8px 12px;
      color: rgba(255,247,237,.8);
      font-size: .78rem;
      font-weight: 900;
      white-space: nowrap;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 22px;
    }

    .card {
      overflow: hidden;
      border: 1px solid rgba(255,255,255,.62);
      border-radius: 26px;
      background: var(--paper);
      box-shadow: var(--shadow);
    }

    .card header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 18px 20px;
      border-bottom: 1px solid var(--line);
    }

    .card p {
      margin: 0 0 4px;
      color: #a64317;
      font-size: .78rem;
      font-weight: 950;
      letter-spacing: .14em;
      text-transform: uppercase;
    }

    .card h2 {
      margin: 0;
      color: var(--ink);
      font-size: .98rem;
      line-height: 1.25;
      font-weight: 850;
    }

    .open,
    .card nav a {
      display: inline-flex;
      min-height: 36px;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      font-size: .82rem;
      font-weight: 950;
      text-decoration: none;
      white-space: nowrap;
      padding: 0 13px;
    }

    .open {
      border: 0;
      color: #fff;
      background: linear-gradient(135deg, var(--orange), #ff8324);
      box-shadow: 0 14px 28px rgba(255,90,31,.24);
    }

    .shot {
      height: 560px;
      overflow: auto;
      padding: 14px;
      background:
        linear-gradient(90deg, rgba(255,255,255,.34) 1px, transparent 1px),
        linear-gradient(180deg, rgba(255,255,255,.34) 1px, transparent 1px),
        #f0ddc2;
      background-size: 28px 28px;
    }

    .shot img {
      display: block;
      width: 100%;
      height: auto;
      min-width: 720px;
      border-radius: 18px;
      border: 1px solid rgba(74,45,25,.14);
      background: #fff;
    }

    .card nav {
      display: flex;
      gap: 10px;
      padding: 14px 18px 18px;
      border-top: 1px solid var(--line);
    }

    .note {
      margin: 18px 0 0;
      color: rgba(255,247,237,.62);
      font-size: .8rem;
      font-weight: 750;
    }

    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .top { align-items: flex-start; flex-direction: column; }
      .badge { white-space: normal; }
    }
  </style>
</head>
<body>
  <main class="wrap">
    <header class="top">
      <div>
        <h1>FutureFunded Canonical Launch Surfaces</h1>
        <p>Only homepage, campaign, onboarding, and private dashboard. Aliases and support routes are audited separately.</p>
      </div>
      <span class="badge">Generated ${esc(stamp)}</span>
    </header>

    <section class="grid">
      ${cards}
    </section>

    <p class="note">Dashboard token is used only during screenshot capture and is not embedded in this board HTML.</p>
  </main>
</body>
</html>`;

  fs.writeFileSync(path.join(out, "index.html"), htmlDoc);
})();
NODE

echo
echo "== Screenshot proof =="
cat "$OUT/screenshot-proof.txt"

echo
echo "== Generate report =="
python - "$OUT" <<'PY'
import csv
from pathlib import Path
import sys

out = Path(sys.argv[1])

rows = list(csv.DictReader((out / "launch-surfaces.csv").open()))

canonical = [r for r in rows if r["kind"] == "canonical"]
aliases = [r for r in rows if r["kind"] == "alias"]
support = [r for r in rows if r["kind"] == "support"]
bad = [r for r in canonical if r["ok"] != "yes"]

def table(items, cols):
    if not items:
        return "_None._"
    text = "| " + " | ".join(cols) + " |\n"
    text += "| " + " | ".join("---" for _ in cols) + " |\n"
    for item in items:
        text += "| " + " | ".join(str(item.get(c, "")).replace("|", "\\|") for c in cols) + " |\n"
    return text

report = f"""# FutureFunded Canonical Launch Surface Audit

## Executive Summary

| Area | Count |
|---|---:|
| Canonical launch surfaces | {len(canonical)} |
| Canonical failures | {len(bad)} |
| Aliases audited but not boarded | {len(aliases)} |
| Support routes audited but not boarded | {len(support)} |

## Canonical Surfaces

{table(canonical, ["id", "label", "url_masked", "status", "data_ff_page", "ok", "title"])}

## Aliases

{table(aliases, ["id", "label", "url_masked", "status", "data_ff_page", "ok", "notes"])}

## Support Routes

{table(support, ["id", "label", "url_masked", "status", "data_ff_page", "ok", "notes"])}

## What This Fixes

- `/` is the homepage board.
- `/platform/` is treated as an alias check, not a second homepage.
- `/platform/dashboard` is captured only with the private token.
- Login is audited as a support/security route, not confused with the dashboard.

## Files

- `index.html`
- `screenshot-proof.txt`
- `launch-surfaces.csv`
- `flask-routes.csv`
- `screenshots/`
- `rendered/`
"""

(out / "launch-surface-report.md").write_text(report)
print(report)
PY

echo
echo "== Open canonical launch board =="
xdg-open "$OUT/index.html" >/dev/null 2>&1 || true

echo
echo "✅ Canonical board:"
echo "$OUT/index.html"
echo
echo "✅ Report:"
echo "$OUT/launch-surface-report.md"

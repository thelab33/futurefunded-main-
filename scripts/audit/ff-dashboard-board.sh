#!/usr/bin/env bash
set -euo pipefail

BASE="${FF_BASE_URL:-http://127.0.0.1:5000}"
STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/dashboard-visual-board-${STAMP}"

mkdir -p "$OUT"

echo "== FutureFunded private dashboard screenshot board v4 =="
echo "OUT=$OUT"

declare -a TOKENS=()
declare -a SOURCES=()

add_token() {
  local source="$1"
  local token="${2:-}"

  token="$(printf '%s' "$token" | tr -d '\r\n\t ')"
  [ -z "$token" ] && return 0

  for existing in "${TOKENS[@]:-}"; do
    [ "$existing" = "$token" ] && return 0
  done

  TOKENS+=("$token")
  SOURCES+=("$source")
}

echo
echo "== Collect token candidates safely =="

python - <<'PY' > "$OUT/token-candidates-from-urls.tsv"
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import re

paths = []
paths.extend(sorted(Path("audit_outputs").glob("dashboard-token-restore-*/WORKING_DASHBOARD_URL.txt"), reverse=True))

for base in sorted(Path("audit_outputs").glob("*"), reverse=True):
    if base.is_dir() and any(name in base.name for name in ["served-url-lite", "dashboard-token", "dashboard-visual-board"]):
        for file in base.glob("*"):
            if file.is_file() and file.suffix.lower() in [".md", ".csv", ".txt", ".html"]:
                paths.append(file)

seen = set()
for p in paths:
    try:
        text = p.read_text(errors="replace")
    except Exception:
        continue

    for url in re.findall(r"http://127\.0\.0\.1:5000/platform/dashboard\?[^ \n\r\t<>'\"]+", text):
        qs = parse_qs(urlparse(url).query)
        for key in ("access_token", "operator_token", "token"):
            for value in qs.get(key, []):
                value = value.strip()
                if value and value not in seen:
                    seen.add(value)
                    print(f"{p}:{key}\t{value}")
PY

while IFS=$'\t' read -r source token || [ -n "${source:-}" ]; do
  add_token "$source" "${token:-}"
done < "$OUT/token-candidates-from-urls.tsv"

if [ -s /tmp/ff_operator_token ]; then
  add_token "/tmp/ff_operator_token" "$(cat /tmp/ff_operator_token)"
fi

for ENV_FILE in .env.local .env .flaskenv; do
  if [ -f "$ENV_FILE" ]; then
    ENV_TOKEN="$(
      { grep -E '^[[:space:]]*FF_OPERATOR_ACCESS_TOKEN=' "$ENV_FILE" 2>/dev/null || true; } \
        | tail -n 1 \
        | sed -E 's/^[[:space:]]*FF_OPERATOR_ACCESS_TOKEN=//' \
        | sed -E 's/^["'\''"]|["'\''"]$//g'
    )"
    add_token "$ENV_FILE" "$ENV_TOKEN"
  fi
done

if [ -n "${FF_OPERATOR_ACCESS_TOKEN:-}" ]; then
  add_token "shell env FF_OPERATOR_ACCESS_TOKEN" "$FF_OPERATOR_ACCESS_TOKEN"
fi

add_token "dev fallback" "dev-operator-20260529123018"

echo "candidates=${#TOKENS[@]}"

if [ "${#TOKENS[@]}" -eq 0 ]; then
  echo "❌ No operator token candidates found."
  exit 1
fi

ensure_server() {
  if ! curl -fsS "$BASE/healthz" >/dev/null; then
    ffserver restart
  fi
}

probe_tokens() {
  local phase="$1"

  WINNER_TOKEN=""
  WINNER_SOURCE=""
  WINNER_KEY=""
  WINNER_HTML=""

  echo
  echo "== Validate token candidates without printing token: $phase =="

  for i in "${!TOKENS[@]}"; do
    local token="${TOKENS[$i]}"
    local source="${SOURCES[$i]}"

    for key in access_token operator_token token; do
      local html="$OUT/probe-${phase}-${i}-${key}.html"
      local url="${BASE}/platform/dashboard?${key}=${token}&dashboard_board_probe=${STAMP}_${phase}_${i}_${key}"

      curl -fsSL "$url" -o "$html" || true

      local result
      result="$(
        python - "$html" <<'PY'
from pathlib import Path
import re
import sys

html = Path(sys.argv[1]).read_text(errors="replace") if Path(sys.argv[1]).exists() else ""

page = re.search(r'<html[^>]*data-ff-page=["\']([^"\']+)["\']', html, re.I)
title = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)

page_value = page.group(1) if page else "NONE"
title_value = " ".join(title.group(1).split()) if title else "NONE"
has_dashboard_js = "ff-operator-dashboard.js" in html
is_login_gate = "ff-loginAuthority" in html or "Organizer access" in title_value
valid = page_value == "platform-dashboard" and has_dashboard_js and not is_login_gate

print(f"page={page_value}")
print(f"title={title_value}")
print(f"dashboard_js={has_dashboard_js}")
print(f"login_gate={is_login_gate}")
print(f"valid_dashboard={'true' if valid else 'false'}")
PY
      )"

      {
        echo "source=$source"
        echo "key=$key"
        echo "token_length=${#token}"
        echo "$result"
      } > "$OUT/probe-${phase}-${i}-${key}.txt"

      local page valid
      page="$(printf '%s\n' "$result" | awk -F= '/^page=/{print $2}')"
      valid="$(printf '%s\n' "$result" | awk -F= '/^valid_dashboard=/{print $2}')"

      echo "candidate=$source key=$key length=${#token} page=$page valid=$valid"

      if [ "$valid" = "true" ]; then
        WINNER_TOKEN="$token"
        WINNER_SOURCE="$source"
        WINNER_KEY="$key"
        WINNER_HTML="$html"
        return 0
      fi
    done
  done

  return 1
}

ensure_server

if ! probe_tokens "before_restart"; then
  echo
  echo "== No valid dashboard token accepted by current server =="
  echo "Restarting Flask with best recovered token exported."

  RESTART_TOKEN=""
  for i in "${!TOKENS[@]}"; do
    if [ "${SOURCES[$i]}" != "dev fallback" ]; then
      RESTART_TOKEN="${TOKENS[$i]}"
      break
    fi
  done

  if [ -z "$RESTART_TOKEN" ]; then
    RESTART_TOKEN="${TOKENS[0]}"
  fi

  printf '%s\n' "$RESTART_TOKEN" > /tmp/ff_operator_token
  chmod 600 /tmp/ff_operator_token

  python - "$RESTART_TOKEN" <<'PY'
from pathlib import Path
import sys

token = sys.argv[1].strip()
p = Path(".env.local")
lines = p.read_text(errors="replace").splitlines() if p.exists() else []

out = []
seen = False
for line in lines:
    if line.strip().startswith("FF_OPERATOR_ACCESS_TOKEN="):
        out.append(f"FF_OPERATOR_ACCESS_TOKEN={token}")
        seen = True
    else:
        out.append(line)

if not seen:
    out.append(f"FF_OPERATOR_ACCESS_TOKEN={token}")

p.write_text("\n".join(out).rstrip() + "\n")
print("✅ refreshed .env.local operator token")
PY

  export FF_OPERATOR_ACCESS_TOKEN="$RESTART_TOKEN"
  export FF_DASHBOARD_AUDIT_TOKEN="$RESTART_TOKEN"

  ffserver restart

  if ! probe_tokens "after_restart"; then
    echo
    echo "❌ No token candidate rendered the private dashboard after restart."
    echo "Probe folder: $OUT"
    sed -n '1,90p' "$OUT"/probe-*.txt
    exit 1
  fi
fi

echo
echo "✅ Valid dashboard token source: $WINNER_SOURCE"
echo "✅ Valid query key: $WINNER_KEY"
echo "✅ Token length: ${#WINNER_TOKEN}"

cp -f "$WINNER_HTML" "$OUT/dashboard-proof.html"

echo
echo "== Playwright availability =="
if ! node -e "require('playwright')" >/dev/null 2>&1; then
  echo "❌ Node package 'playwright' is not available."
  echo "Try: npm install -D playwright && npx playwright install chromium"
  exit 1
fi

echo "✅ Playwright available"

echo
echo "== Capture dashboard screenshots =="
WINNER_TOKEN="$WINNER_TOKEN" \
WINNER_KEY="$WINNER_KEY" \
BASE="$BASE" \
OUT="$OUT" \
STAMP="$STAMP" \
node <<'NODE'
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const base = process.env.BASE;
const token = process.env.WINNER_TOKEN;
const key = process.env.WINNER_KEY;
const out = process.env.OUT;
const stamp = process.env.STAMP;

const url = `${base}/platform/dashboard?${encodeURIComponent(key)}=${encodeURIComponent(token)}&screenshot_board=${encodeURIComponent(stamp)}`;

const viewports = [
  { name: "desktop", label: "Desktop", width: 1440, height: 1600, note: "Full operator command center" },
  { name: "tablet", label: "Tablet", width: 834, height: 1400, note: "Stacking and right-rail behavior" },
  { name: "mobile", label: "Mobile", width: 390, height: 1200, note: "Small-screen operator workflow" },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const proof = [];

  for (const vp of viewports) {
    const page = await browser.newPage({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 1,
    });

    await page.goto(url + `&viewport=${vp.name}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });

    const pageName = await page.locator("html").getAttribute("data-ff-page").catch(() => "NONE");
    const hasDashboardJs = (await page.content()).includes("ff-operator-dashboard.js");
    const title = await page.title();

    proof.push(`${vp.name}: page=${pageName} dashboard_js=${hasDashboardJs} title=${title}`);

    if (pageName !== "platform-dashboard" || !hasDashboardJs) {
      throw new Error(`Invalid dashboard render for ${vp.name}: page=${pageName}, js=${hasDashboardJs}`);
    }

    await page.screenshot({
      path: path.join(out, `${vp.name}.png`),
      fullPage: true,
      animations: "disabled",
    });

    await page.close();
  }

  await browser.close();

  fs.writeFileSync(path.join(out, "screenshot-proof.txt"), proof.join("\n") + "\n");

  const esc = (s) => String(s).replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[m]));

  const cards = viewports.map((vp) => `
    <section class="boardCard">
      <header>
        <div>
          <strong>${esc(vp.label)}</strong>
          <span>${vp.width}px preview · ${esc(vp.note)}</span>
        </div>
        <a href="${vp.name}.png" target="_blank" rel="noopener">Open PNG</a>
      </header>
      <div class="shotWrap">
        <img src="${vp.name}.png" alt="${esc(vp.label)} dashboard screenshot">
      </div>
    </section>
  `).join("\n");

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>FutureFunded Dashboard Screenshot Board</title>
  <style>
    :root {
      --bg: #f1ddc0;
      --card: rgba(255,252,246,.92);
      --ink: #21140c;
      --muted: rgba(47,31,20,.62);
      --line: rgba(76,49,30,.14);
      --orange: #ff5a1f;
      --shadow: 0 24px 70px rgba(61,38,20,.13);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 10% -10%, rgba(255,90,31,.16), transparent 24rem),
        radial-gradient(circle at 90% 0%, rgba(15,118,110,.10), transparent 26rem),
        linear-gradient(180deg, #fff7ec 0%, var(--bg) 100%);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .board {
      width: min(100% - 28px, 1520px);
      margin: 0 auto;
      padding: 24px 0 46px;
    }
    .topbar {
      position: sticky;
      top: 12px;
      z-index: 5;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      border: 1px solid rgba(255,255,255,.72);
      border-radius: 999px;
      background: rgba(255,252,246,.88);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
      padding: 10px 14px;
      margin-bottom: 18px;
    }
    .brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
    .mark {
      display: grid;
      width: 36px;
      height: 36px;
      place-items: center;
      border-radius: 13px;
      background: linear-gradient(135deg, #140b07, #5b2410);
      color: #fff8ee;
      font-size: .72rem;
      font-weight: 950;
    }
    h1 { margin: 0; font-size: clamp(1rem, 1.8vw, 1.45rem); line-height: 1; letter-spacing: -.04em; }
    p { margin: 3px 0 0; color: var(--muted); font-size: .82rem; font-weight: 750; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .actions a,
    .boardCard header a {
      display: inline-flex;
      min-height: 36px;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      color: var(--ink);
      background: #fff;
      border: 1px solid var(--line);
      text-decoration: none;
      font-size: .78rem;
      font-weight: 900;
      padding: 0 13px;
    }
    .actions a.primary {
      color: #fff;
      border-color: transparent;
      background: linear-gradient(135deg, var(--orange), #ff8324);
      box-shadow: 0 12px 24px rgba(255,90,31,.22);
    }
    .grid { display: grid; grid-template-columns: 1fr; gap: 18px; }
    .boardCard {
      border: 1px solid rgba(255,255,255,.74);
      border-radius: 26px;
      background: var(--card);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .boardCard > header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      border-bottom: 1px solid var(--line);
      padding: 14px 16px;
    }
    .boardCard strong { display: block; font-size: .9rem; letter-spacing: -.02em; }
    .boardCard span { color: var(--muted); font-size: .76rem; font-weight: 750; }
    .shotWrap {
      overflow: auto;
      padding: 14px;
      background: linear-gradient(135deg, rgba(255,255,255,.42), rgba(255,244,229,.36));
    }
    img {
      display: block;
      max-width: min(100%, 1440px);
      height: auto;
      margin: 0 auto;
      border: 1px solid rgba(76,49,30,.16);
      border-radius: 22px;
      background: #fff;
      box-shadow: 0 18px 44px rgba(61,38,20,.12);
    }
    .note { margin: 18px 0 0; color: var(--muted); font-size: .78rem; font-weight: 750; }
    @media (max-width: 760px) {
      .topbar { align-items: flex-start; border-radius: 22px; flex-direction: column; }
      .actions { width: 100%; justify-content: stretch; }
      .actions a { flex: 1; }
    }
  </style>
</head>
<body>
  <main class="board">
    <header class="topbar">
      <div class="brand">
        <span class="mark">FF</span>
        <div>
          <h1>Dashboard screenshot board</h1>
          <p>Private operator dashboard · generated ${esc(stamp)} · screenshots avoid iframe security blocking</p>
        </div>
      </div>
      <nav class="actions" aria-label="Board actions">
        <a class="primary" href="desktop.png" target="_blank" rel="noopener">Open desktop PNG</a>
        <a href="screenshot-proof.txt" target="_blank" rel="noopener">Proof</a>
      </nav>
    </header>

    <section class="grid">
      ${cards}
    </section>

    <p class="note">Safe to view locally. Do not commit audit_outputs. Token is not embedded in this board HTML.</p>
  </main>
</body>
</html>`;

  fs.writeFileSync(path.join(out, "index.html"), html);
})();
NODE

echo
echo "== Screenshot proof =="
cat "$OUT/screenshot-proof.txt"

echo
echo "== Served URL audit quietly =="
FF_OPERATOR_ACCESS_TOKEN="$WINNER_TOKEN" FF_DASHBOARD_AUDIT_TOKEN="$WINNER_TOKEN" bash scripts/audit/ff-served-url-lite.sh >/dev/null

LATEST="$(
  find audit_outputs -maxdepth 1 -type d -name 'served-url-lite-*' -printf '%T@ %p\n' \
    | sort -nr \
    | awk 'NR==1{print $2}'
)"

grep -E "Served rows|Broken rows" "$LATEST/README.md"

cat > "$OUT/open-dashboard.sh" <<BASH2
#!/usr/bin/env bash
set -euo pipefail
xdg-open "${BASE}/platform/dashboard?${WINNER_KEY}=${WINNER_TOKEN}" >/dev/null 2>&1 &
BASH2
chmod 700 "$OUT/open-dashboard.sh"

echo
echo "== Open screenshot board =="
xdg-open "$OUT/index.html" >/dev/null 2>&1 || true

echo
echo "✅ Screenshot board:"
echo "$OUT/index.html"
echo
echo "✅ Direct dashboard opener:"
echo "$OUT/open-dashboard.sh"

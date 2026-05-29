#!/usr/bin/env bash
set -Eeuo pipefail

STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/spine-gate/${STAMP}"
BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5011}"
PORT="${FF_GATE_PORT:-5011}"

mkdir -p "$OUT"/{reports,screenshots,rendered}

echo "== FutureFunded Product Spine Gate =="
echo "Output: $OUT"
echo

echo "== Git state =="
{
  echo "Branch: $(git branch --show-current)"
  echo "HEAD:   $(git rev-parse HEAD)"
  echo
  echo "Tags at HEAD:"
  git tag --points-at HEAD || true
  echo
  echo "Status:"
  git status --short
} | tee "$OUT/reports/git-state.txt"

git diff > "$OUT/reports/working-tree.diff" || true
git diff --stat > "$OUT/reports/working-tree.stat" || true

echo
echo "== Product-spine shape check =="
REQUIRED=(
  "apps/web/app/static/css"
  "apps/web/app/static/js"
  "apps/web/app/templates"
  "apps/web/app/__init__.py"
  "scripts"
  "tests"
  "migrations"
)

for path in "${REQUIRED[@]}"; do
  if [ ! -e "$path" ]; then
    echo "FAIL missing $path" | tee -a "$OUT/reports/shape-check.txt"
    exit 1
  fi
  echo "OK $path" | tee -a "$OUT/reports/shape-check.txt"
done

if [ -d apps/apps ] || [ -d scripts/scripts ] || [ -d tests/tests ]; then
  echo "FAIL nested copy bug detected" | tee -a "$OUT/reports/shape-check.txt"
  exit 1
fi

echo
echo "== CSS brace check =="
python - <<'PY' | tee "$OUT/reports/css-brace-check.txt"
from pathlib import Path
import re
import sys

bad = False
for p in [
    Path("apps/web/app/static/css/ff.css"),
    Path("apps/web/app/static/css/campaign.css"),
    Path("apps/web/app/static/css/onboarding.css"),
]:
    if not p.exists():
        print(f"FAIL\t{p}\tmissing")
        bad = True
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    clean = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    opens = clean.count("{")
    closes = clean.count("}")
    ok = opens == closes
    print(f"{'OK' if ok else 'FAIL'}\t{p}\t{{={opens}\t}}={closes}\t!important={text.count('!important')}")
    bad = bad or not ok

if bad:
    sys.exit(1)
PY

echo
echo "== Start isolated Flask server on ${BASE_URL} =="
SERVER_LOG="$OUT/reports/flask-gate.log"
SERVER_PID_FILE="$OUT/reports/flask-gate.pid"

cleanup() {
  if [ -f "$SERVER_PID_FILE" ]; then
    pid="$(cat "$SERVER_PID_FILE" || true)"
    if [ -n "${pid:-}" ]; then
      kill "$pid" 2>/dev/null || true
    fi
  fi
}
trap cleanup EXIT

# Clear only the selected gate port.
PIDS="$(ss -ltnp 2>/dev/null | grep ":${PORT}" | sed -nE 's/.*pid=([0-9]+).*/\1/p' | sort -u || true)"
for pid in $PIDS; do
  echo "Stopping existing listener on ${PORT}: pid=$pid"
  kill -TERM "$pid" 2>/dev/null || true
done
sleep 1

nohup env \
  FLASK_DEBUG=0 \
  FLASK_ENV=production \
  python -m flask \
    --app apps.web.app:create_app \
    run \
    --no-debugger \
    --no-reload \
    --host 127.0.0.1 \
    --port "$PORT" \
  > "$SERVER_LOG" 2>&1 &

echo $! > "$SERVER_PID_FILE"
sleep 5

if ! curl -k -sS -o /dev/null "$BASE_URL/platform/" 2>/dev/null; then
  echo "❌ Flask did not respond."
  tail -160 "$SERVER_LOG" || true
  exit 1
fi

echo "✅ Flask responded."

echo
echo "== Route preflight =="
ROUTES=(
  "/platform/"
  "/c/connect-atx-elite"
  "/platform/login"
  "/platform/onboarding"
  "/platform/dashboard"
)

: > "$OUT/reports/route-preflight.txt"

for route in "${ROUTES[@]}"; do
  code="$(curl -k -sS -o /dev/null -w "%{http_code}" "$BASE_URL$route?spine_gate=$STAMP" || true)"
  printf "%s\t%s\n" "$code" "$BASE_URL$route" | tee -a "$OUT/reports/route-preflight.txt"

  case "$route:$code" in
    "/platform/:200"|"/c/connect-atx-elite:200"|"/platform/login:200"|"/platform/onboarding:200")
      ;;
    "/platform/dashboard:302"|"/platform/dashboard:403"|"/platform/dashboard:200")
      ;;
    *)
      echo "❌ Unexpected route status for $route: $code"
      exit 1
      ;;
  esac
done


echo
echo "== Browser dependency preflight =="
if ! node - <<'NODE'
let ok = false;
try {
  require("playwright");
  ok = true;
} catch (_) {}

try {
  require("@playwright/test");
  ok = true;
} catch (_) {}

if (!ok) {
  console.error("❌ Missing Playwright dependency.");
  console.error("Run:");
  console.error("  npm ci --include=dev");
  console.error("  npx playwright install chromium");
  process.exit(1);
}
console.log("✅ Playwright dependency available.");
NODE
then
  exit 1
fi

echo
echo "== Build browser contract audit =="
cat > "$OUT/rendered/spine-browser-gate.cjs" <<'NODE'
const fs = require("fs");
const path = require("path");

let chromium;
try {
  chromium = require("playwright").chromium;
} catch {
  chromium = require("@playwright/test").chromium;
}

const out = process.argv[2];
const baseUrl = process.argv[3];

const pages = [
  { label: "platform-home", route: "/platform/", requiredStatus: [200], requiredHooks: [] },
  {
    label: "campaign",
    route: "/c/connect-atx-elite",
    requiredStatus: [200],
    requiredHooks: [
      "[data-ff-open-checkout]",
      "[data-ff-donate-trigger]",
      "[data-ff-payment-trigger]",
      "[data-ff-sponsor-trigger]",
      "[data-ff-share-trigger]",
      "[data-ff-qr-trigger]"
    ]
  },
  { label: "login", route: "/platform/login", requiredStatus: [200], requiredHooks: [] },
  { label: "onboarding", route: "/platform/onboarding", requiredStatus: [200], requiredHooks: [] },
  { label: "dashboard", route: "/platform/dashboard", requiredStatus: [200, 302, 403], requiredHooks: [] }
];

const viewports = [
  { label: "mobile", width: 390, height: 844 },
  { label: "tablet", width: 820, height: 1180 },
  { label: "desktop", width: 1440, height: 1100 }
];

async function inspect(page, spec) {
  return page.evaluate((requiredHooks) => {
    const html = document.documentElement;

    const linkedCss = Array.from(document.querySelectorAll('link[rel~="stylesheet"]')).map(link => ({
      href: link.href,
      media: link.media || "",
      disabled: link.disabled
    }));

    const hookCounts = Object.fromEntries(
      requiredHooks.map(sel => [sel, document.querySelectorAll(sel).length])
    );

    const dataAttrs = {};
    document.querySelectorAll("*").forEach(el => {
      Array.from(el.attributes || []).forEach(attr => {
        if (attr.name.startsWith("data-ff")) {
          dataAttrs[attr.name] = (dataAttrs[attr.name] || 0) + 1;
        }
      });
    });

    const topClasses = {};
    document.querySelectorAll("[class]").forEach(el => {
      String(el.className || "").split(/\s+/).filter(Boolean).forEach(cls => {
        topClasses[cls] = (topClasses[cls] || 0) + 1;
      });
    });

    function box(selector) {
      const el = document.querySelector(selector);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        rect: {
          x: Math.round(r.x),
          y: Math.round(r.y),
          w: Math.round(r.width),
          h: Math.round(r.height)
        },
        display: cs.display,
        position: cs.position,
        top: cs.top,
        bottom: cs.bottom,
        zIndex: cs.zIndex
      };
    }

    return {
      title: document.title,
      metrics: {
        scrollWidth: html.scrollWidth,
        clientWidth: html.clientWidth,
        horizontalOverflow: html.scrollWidth > html.clientWidth + 2,
        bodyHeight: document.body.scrollHeight,
        h1Count: document.querySelectorAll("h1").length
      },
      linkedCss,
      hookCounts,
      dataAttrs: Object.entries(dataAttrs).sort((a, b) => b[1] - a[1]).slice(0, 120),
      topClasses: Object.entries(topClasses).sort((a, b) => b[1] - a[1]).slice(0, 120),
      boxes: {
        header: box("[data-ff-header]"),
        hero: box(".ff-campaignHero, .ff-homeHero, [data-ff-hero]"),
        campaignStory: box(".ff-campaignHero__story"),
        donatePanel: box(".ff-donatePanel"),
        checkoutModal: box(".ff-checkoutModal, [data-ff-checkout-modal], [data-ff-donation-modal]")
      }
    };
  }, spec.requiredHooks);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const rows = [];

  for (const spec of pages) {
    for (const vp of viewports) {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 1,
        reducedMotion: "reduce"
      });

      const page = await context.newPage();
      const events = [];

      page.on("console", msg => {
        if (["error", "warning"].includes(msg.type())) {
          events.push(`${msg.type()}: ${msg.text()}`.slice(0, 900));
        }
      });

      const row = {
        page: spec.label,
        route: spec.route,
        viewport: vp.label,
        status: null,
        finalUrl: "",
        data: null,
        screenshot: "",
        events,
        failed: []
      };

      try {
        const res = await page.goto(`${baseUrl}${spec.route}?spine_gate=${Date.now()}`, {
          waitUntil: "networkidle",
          timeout: 60000
        });

        row.status = res ? res.status() : null;
        row.finalUrl = page.url();

        await page.evaluate(async () => {
          if (document.fonts && document.fonts.ready) await document.fonts.ready;
        }).catch(() => {});
        await page.waitForTimeout(700);

        row.data = await inspect(page, spec);

        if (!spec.requiredStatus.includes(row.status)) {
          row.failed.push(`unexpected HTTP ${row.status}`);
        }

        if (row.data.metrics.horizontalOverflow) {
          row.failed.push("horizontal overflow");
        }

        for (const [hook, count] of Object.entries(row.data.hookCounts || {})) {
          if (count < 1) row.failed.push(`missing hook ${hook}`);
        }

        if (spec.label !== "dashboard" && row.data.linkedCss.length < 1) {
          row.failed.push("no linked CSS");
        }

        const shot = path.join(out, "screenshots", `${spec.label}-${vp.label}.png`);
        await page.screenshot({ path: shot, fullPage: true });
        row.screenshot = shot;
      } catch (err) {
        row.failed.push(String(err && err.stack ? err.stack : err));
      }

      rows.push(row);
      await context.close();
    }
  }

  await browser.close();

  fs.writeFileSync(path.join(out, "reports", "spine-browser-gate.json"), JSON.stringify(rows, null, 2));

  const lines = [];
  lines.push("# FutureFunded Product Spine Browser Gate");
  lines.push("");
  lines.push(`Generated: ${new Date().toISOString()}`);
  lines.push("");
  lines.push("| Page | Viewport | HTTP | CSS links | Overflow | H1 | Header | Hero | Donate | Findings | Screenshot |");
  lines.push("|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|");

  let failed = false;

  for (const row of rows) {
    const d = row.data || {};
    const b = d.boxes || {};
    const result = row.failed.length ? row.failed.join("; ") : "PASS";
    if (row.failed.length) failed = true;

    lines.push(
      `| ${row.page} | ${row.viewport} | ${row.status ?? "ERR"} | ${d.linkedCss?.length ?? "n/a"} | ${d.metrics?.horizontalOverflow ?? "n/a"} | ${d.metrics?.h1Count ?? "n/a"} | ${b.header?.rect?.h ?? "n/a"} | ${b.hero?.rect?.h ?? "n/a"} | ${b.donatePanel?.rect?.h ?? "n/a"} | ${result} | ${row.screenshot ? row.screenshot.replace(out + "/", "") : "n/a"} |`
    );
  }

  lines.push("");
  lines.push("## Linked CSS");
  for (const row of rows) {
    lines.push("");
    lines.push(`### ${row.page} / ${row.viewport}`);
    for (const css of row.data?.linkedCss || []) {
      lines.push(`- ${css.href}`);
    }
  }

  lines.push("");
  lines.push("## Console warnings/errors");
  for (const row of rows) {
    lines.push("");
    lines.push(`### ${row.page} / ${row.viewport}`);
    if (!row.events.length) lines.push("- none");
    else row.events.slice(0, 12).forEach(e => lines.push(`- ${e}`));
  }

  fs.writeFileSync(path.join(out, "reports", "spine-browser-gate.md"), lines.join("\n"));
  console.log(lines.join("\n"));

  if (failed) process.exit(1);
})();
NODE

set +e
node "$OUT/rendered/spine-browser-gate.cjs" "$OUT" "$BASE_URL" | tee "$OUT/reports/spine-browser-gate-output.txt"
BROWSER_STATUS="${PIPESTATUS[0]}"
set -e

echo
echo "== Create screenshot board =="
cat > "$OUT/index.html" <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FutureFunded Product Spine Gate</title>
  <style>
    body{margin:0;background:#fff7ed;color:#21140c;font-family:Inter,system-ui,sans-serif;padding:28px}
    h1{font-size:clamp(2rem,5vw,4rem);line-height:.9;letter-spacing:-.07em;margin:0 0 12px}
    p{color:rgba(33,20,12,.68)}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:24px}
    a{display:block;border:1px solid rgba(74,44,22,.15);border-radius:24px;background:white;padding:20px;color:#21140c;text-decoration:none;box-shadow:0 18px 48px rgba(55,36,20,.1);font-weight:850}
    span{display:block;color:#f35f16;margin-top:6px}
  </style>
</head>
<body>
  <h1>FutureFunded Product Spine Gate</h1>
  <p>Open screenshots and report before committing any UI patch.</p>
  <div class="grid">
    <a href="./reports/spine-browser-gate.md">Gate report<span>metrics + findings</span></a>
    <a href="./reports/git-state.txt">Git state<span>branch, head, dirty diff</span></a>
    <a href="./reports/css-brace-check.txt">CSS brace check<span>ff / campaign / onboarding</span></a>
    <a href="./screenshots/campaign-mobile.png">Campaign mobile<span>highest-risk view</span></a>
    <a href="./screenshots/campaign-tablet.png">Campaign tablet<span>mid-size view</span></a>
    <a href="./screenshots/campaign-desktop.png">Campaign desktop<span>wide view</span></a>
    <a href="./screenshots/platform-home-mobile.png">Homepage mobile<span>sales surface</span></a>
    <a href="./screenshots/onboarding-mobile.png">Onboarding mobile<span>form surface</span></a>
  </div>
</body>
</html>
HTML

rm -f audit_outputs/spine-gate/latest
ln -s "$(basename "$OUT")" audit_outputs/spine-gate/latest

echo
echo "== Done =="
echo "Report:"
echo "  $OUT/reports/spine-browser-gate.md"
echo
echo "Open board:"
echo "  python -m http.server 8773 -d audit_outputs/spine-gate/latest"
echo "  http://127.0.0.1:8773/"
echo

if [ "$BROWSER_STATUS" -ne 0 ]; then
  echo "⚠️ Browser gate found issues. Inspect report/screenshots before patching."
  exit "$BROWSER_STATUS"
fi

echo "✅ Product spine gate passed."

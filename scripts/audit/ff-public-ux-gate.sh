#!/usr/bin/env bash
set -uo pipefail

ROOT="${1:-$(pwd)}"
BASE_URL="${BASE_URL:-http://127.0.0.1:5000}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/audit_outputs/public-ux-gate/$STAMP"

mkdir -p "$OUT"
cd "$ROOT" || exit 1

fail=0
warn=0

pass() { echo "✅ $*"; }
soft() { echo "⚠️ $*"; warn=$((warn+1)); }
bad() { echo "❌ $*"; fail=$((fail+1)); }

echo
echo "FutureFunded Public UX Gate"
echo "Root: $ROOT"
echo "Base: $BASE_URL"
echo "Out:  $OUT"
echo

echo "▶ Required files"
echo "------------------------------------------------------------"

for file in \
  "apps/web/app/templates/platform/index.html" \
  "apps/web/app/templates/campaign/index.html" \
  "apps/web/app/static/css/ff.css" \
  "apps/web/app/static/css/campaign.css"
do
  [[ -f "$file" ]] && pass "$file" || bad "$file missing"
done

echo
echo "▶ High-signal static checks"
echo "------------------------------------------------------------"

ACTIVE_FILES=(
  "apps/web/app/templates/platform/index.html"
  "apps/web/app/templates/campaign/index.html"
  "apps/web/app/static/css/ff.css"
  "apps/web/app/static/css/campaign.css"
)

if grep -RInE "lorem ipsum|replace me|dummy copy|sample copy|demo only|TODO|FIXME|built to help \{\{|_safe_campaign_name" "${ACTIVE_FILES[@]}" > "$OUT/static-high-signal-hits.txt" 2>/dev/null; then
  bad "High-signal placeholder/leak terms found"
  cat "$OUT/static-high-signal-hits.txt"
else
  pass "No high-signal placeholder/demo/leak terms in active public files"
fi

echo
echo "▶ CSS brace balance"
echo "------------------------------------------------------------"

set +e
node - "$ROOT/apps/web/app/static/css/ff.css" "$ROOT/apps/web/app/static/css/campaign.css" "$OUT/css-balance.json" <<'NODE'
const fs = require("fs");

const files = process.argv.slice(2, 4);
const out = process.argv[4];
let failed = false;

function stripCssComments(input) {
  return input.replace(/\/\*[\s\S]*?\*\//g, "");
}

const report = files.map((file) => {
  const css = stripCssComments(fs.readFileSync(file, "utf8"));
  const open = (css.match(/\{/g) || []).length;
  const close = (css.match(/\}/g) || []).length;
  const ok = open === close;
  if (!ok) failed = true;
  return { file, open, close, ok };
});

fs.writeFileSync(out, JSON.stringify(report, null, 2));

for (const item of report) {
  console.log(`${item.ok ? "✅" : "❌"} ${item.file}: open=${item.open} close=${item.close}`);
}

process.exit(failed ? 1 : 0);
NODE
CSS_STATUS=$?
set -e

[[ "$CSS_STATUS" -eq 0 ]] && pass "CSS brace balance passed" || bad "CSS brace balance failed"

echo
echo "▶ HTTP render checks"
echo "------------------------------------------------------------"

fetch_page() {
  local label="$1"
  local path="$2"
  local html="$OUT/${label}.html"
  local text="$OUT/${label}-rendered-visible-text.txt"

  local code
  code="$(curl -k -L -sS -o "$html" -w "%{http_code}" "$BASE_URL$path" || true)"

  if [[ "$code" =~ ^2|^3 ]]; then
    pass "$path HTTP $code"
  else
    bad "$path HTTP $code"
  fi

  python - "$html" "$text" <<'PYTEXT'
from html.parser import HTMLParser
from pathlib import Path
import sys

html_path = Path(sys.argv[1])
text_path = Path(sys.argv[2])

class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "template"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            cleaned = " ".join(data.split())
            if cleaned:
                self.parts.append(cleaned)

parser = VisibleTextParser()
parser.feed(html_path.read_text(errors="ignore"))
text_path.write_text("\n".join(parser.parts))
PYTEXT

  if grep -E "\{\{|\}\}|{%|%}" "$text" >/dev/null 2>&1; then
    bad "$path rendered visible Jinja leak detected"
    grep -nE "\{\{|\}\}|{%|%}" "$text" | head -20 > "$OUT/${label}-rendered-jinja-leaks.txt"
    cat "$OUT/${label}-rendered-jinja-leaks.txt"
  else
    pass "$path no rendered visible Jinja leaks"
  fi

  if grep -iE "lorem ipsum|replace me|dummy copy|sample copy|demo only|coming soon" "$text" >/dev/null 2>&1; then
    bad "$path rendered placeholder/demo copy detected"
    grep -inE "lorem ipsum|replace me|dummy copy|sample copy|demo only|coming soon" "$text" | head -20 > "$OUT/${label}-rendered-placeholder-hits.txt"
    cat "$OUT/${label}-rendered-placeholder-hits.txt"
  else
    pass "$path no rendered placeholder/demo copy"
  fi
}

fetch_page "platform" "/platform/"
fetch_page "campaign" "/c/connect-atx-elite"

echo
echo "▶ Payment endpoint checks"
echo "------------------------------------------------------------"

CONFIG_CODE="$(curl -k -sS -o "$OUT/payments-config.json" -w "%{http_code}" "$BASE_URL/c/connect-atx-elite/payments/config" || true)"
if [[ "$CONFIG_CODE" =~ ^2 ]]; then
  pass "payments/config HTTP $CONFIG_CODE"
else
  soft "payments/config HTTP $CONFIG_CODE"
fi

SESSION_CODE="$(curl -k -sS -o "$OUT/checkout-session.json" -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -X POST \
  --data '{"amount":25,"amount_cents":2500,"frequency":"one_time","campaign_slug":"connect-atx-elite","metadata":{"source":"public-ux-gate","no_charge":true}}' \
  "$BASE_URL/c/connect-atx-elite/checkout/session" || true)"

if [[ "$SESSION_CODE" =~ ^2|^3|^4 ]]; then
  pass "checkout/session reachable HTTP $SESSION_CODE — no card charged"
else
  bad "checkout/session unreachable HTTP $SESSION_CODE"
fi

echo
echo "▶ Browser UX gate"
echo "------------------------------------------------------------"

set +e
node - "$BASE_URL" "$OUT" <<'NODE'
const fs = require("fs");
const path = require("path");

const baseURL = process.argv[2];
const outDir = process.argv[3];

(async () => {
  let chromium;
  try {
    chromium = require("playwright").chromium;
  } catch {
    console.log("⚠️ Playwright missing. Run: npm i -D playwright && npx playwright install chromium");
    fs.writeFileSync(path.join(outDir, "browser-skipped.json"), JSON.stringify({ skipped: true, reason: "playwright_missing" }, null, 2));
    process.exit(2);
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 }, deviceScaleFactor: 1 });

  const results = [];
  const add = (name, ok, data = {}) => results.push({ name, ok, ...data });

  async function auditPage(label, route) {
    await page.goto(`${baseURL}${route}`, { waitUntil: "networkidle", timeout: 30000 });
    await page.screenshot({ path: path.join(outDir, `${label}-desktop.png`), fullPage: true });

    const data = await page.evaluate(() => {
      const text = document.body.innerText || "";
      const doc = document.documentElement;
      return {
        title: document.title,
        bodyChars: text.length,
        overflowX: Math.ceil(doc.scrollWidth - doc.clientWidth),
        hasRenderedJinja: /\{\{|\}\}|{%|%}/.test(text),
        hasPlaceholderCopy: /lorem ipsum|replace me|dummy copy|sample copy|demo only|coming soon/i.test(text),
        selectors: {
          checkout: document.querySelectorAll("[data-ff-open-checkout], [data-ff-donate-trigger], [data-ff-payment-trigger]").length,
          sponsor: document.querySelectorAll("[data-ff-open-sponsor], [data-ff-sponsor-trigger]").length,
          share: document.querySelectorAll("[data-ff-share-trigger], [data-ff-qr-trigger]").length,
          pageRoot: document.querySelectorAll("[data-ff-page-root]").length,
          campaignConfig: document.querySelectorAll("#ffCampaignConfig, script[type='application/json'][data-ff-campaign-config]").length,
          campaignJsContract: document.querySelectorAll("[data-ff-campaign-js], [data-ff-checkout-js-contract]").length,
        },
      };
    });

    add(`${label}: page content`, data.bodyChars > 1000, data);
    add(`${label}: no horizontal overflow`, data.overflowX <= 2, data);
    add(`${label}: no rendered Jinja leak`, !data.hasRenderedJinja, data);
    add(`${label}: no placeholder/demo copy`, !data.hasPlaceholderCopy, data);

    if (label === "campaign") {
      add("campaign: checkout CTA exists", data.selectors.checkout > 0, data);
      add("campaign: sponsor CTA exists", data.selectors.sponsor > 0, data);
      add("campaign: share/QR CTA exists", data.selectors.share > 0, data);
      add("campaign: page root exists", data.selectors.pageRoot > 0, data);
    }
  }

  await auditPage("platform", "/platform/");
  await auditPage("campaign", "/c/connect-atx-elite");

  await page.setViewportSize({ width: 390, height: 920 });
  await page.goto(`${baseURL}/c/connect-atx-elite`, { waitUntil: "networkidle", timeout: 30000 });
  await page.screenshot({ path: path.join(outDir, "campaign-mobile.png"), fullPage: true });

  const mobileOverflow = await page.evaluate(() => Math.ceil(document.documentElement.scrollWidth - document.documentElement.clientWidth));
  add("campaign mobile: no horizontal overflow", mobileOverflow <= 2, { overflowX: mobileOverflow });

  async function clickAndDetect(name, clickSelector, detectSelectors) {
    await page.goto(`${baseURL}/c/connect-atx-elite`, { waitUntil: "networkidle", timeout: 30000 });

    const target = await page.evaluateHandle((selector) => {
      const candidates = Array.from(document.querySelectorAll(selector));

      for (const el of candidates) {
        el.removeAttribute("data-ff-gate-click-target");
      }

      const visible = candidates.find((el) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const ariaHidden = el.getAttribute("aria-hidden") === "true";
        const disabled = el.disabled || el.getAttribute("aria-disabled") === "true";
        return (
          !el.hidden &&
          !ariaHidden &&
          !disabled &&
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          Number(style.opacity || 1) > 0 &&
          rect.width > 8 &&
          rect.height > 8
        );
      });

      if (visible) {
        visible.setAttribute("data-ff-gate-click-target", "true");
      }

      return visible || null;
    }, clickSelector);

    const trigger = await page.$("[data-ff-gate-click-target='true']");
    if (!trigger) {
      add(`${name}: visible trigger exists`, false, { clickSelector });
      return;
    }

    await trigger.scrollIntoViewIfNeeded().catch(() => {});
    await trigger.click({ timeout: 8000, force: true }).catch(() => {});
    await page.waitForTimeout(900);

    const opened = await page.evaluate((selectors) => {
      return selectors.some((sel) => {
        const el = document.querySelector(sel);
        if (!el) return false;
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const ariaHidden = el.getAttribute("aria-hidden") === "true";
        return (
          !el.hidden &&
          !ariaHidden &&
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          rect.width > 10 &&
          rect.height > 10
        );
      });
    }, detectSelectors);

    add(`${name}: opens or visible`, opened, { clickSelector, detectSelectors });
  }

  await clickAndDetect(
    "checkout modal",
    "[data-ff-open-checkout], [data-ff-donate-trigger], [data-ff-payment-trigger]",
    ["[data-ff-checkout-modal]", "[data-ff-embedded-checkout-shell]", ".ff-checkoutModal", ".ff-paymentModal", "#give"]
  );

  await clickAndDetect(
    "sponsor modal",
    "[data-ff-open-sponsor], [data-ff-sponsor-trigger]",
    ["[data-ff-sponsor-modal]", "[data-ff-sponsor-form]", ".ff-sponsorModal", "#sponsor-form", "#sponsors"]
  );

  await clickAndDetect(
    "share/QR modal",
    "[data-ff-share-trigger], [data-ff-qr-trigger]",
    ["[data-ff-share-modal]", "[data-ff-qr-modal]", ".ff-shareModal", ".ff-shareDrawer", "[data-ff-share-drawer]"]
  );

  await browser.close();

  const failed = results.filter((r) => !r.ok);
  fs.writeFileSync(path.join(outDir, "browser-results.json"), JSON.stringify({ results, failed }, null, 2));

  for (const r of results) {
    console.log(`${r.ok ? "✅" : "❌"} ${r.name}`);
  }

  process.exit(failed.length ? 1 : 0);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
NODE
BROWSER_STATUS=$?
set -e

if [[ "$BROWSER_STATUS" -eq 0 ]]; then
  pass "Browser UX gate completed"
elif [[ "$BROWSER_STATUS" -eq 2 ]]; then
  soft "Browser UX gate skipped because Playwright is missing"
else
  bad "Browser UX gate failed"
fi

echo
echo "------------------------------------------------------------"
echo "Public UX Gate Summary"
echo "------------------------------------------------------------"
echo "Output: $OUT"
echo "Failures: $fail"
echo "Warnings: $warn"

if [[ "$fail" -eq 0 ]]; then
  echo "✅ PUBLIC UX GATE PASSED"
  exit 0
fi

echo "❌ PUBLIC UX GATE FAILED"
exit 1

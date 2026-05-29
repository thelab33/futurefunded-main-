#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT = path.join(ROOT, "audit_outputs");
fs.mkdirSync(OUT, { recursive: true });

const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "");
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
const page = await browser.newPage({ viewport: { width: 390, height: 900 }, isMobile: true, hasTouch: true });

const issues = [];
page.on("console", (msg) => {
  if (["error", "warning"].includes(msg.type())) {
    const text = msg.text();
    if (!/favicon|source map|devtools/i.test(text)) issues.push(`${msg.type()}: ${text}`);
  }
});
page.on("pageerror", (err) => issues.push(`pageerror: ${err.message}`));

const res = await page.goto("http://127.0.0.1:5000/c/connect-atx-elite?qa=wave10a-sponsor", {
  waitUntil: "domcontentloaded",
  timeout: 20000
});
await page.waitForTimeout(900);

const screenshot = path.join(OUT, `ff_wave10a_sponsor_sales_${stamp}.png`);
await page.screenshot({ path: screenshot, fullPage: true });

const data = await page.evaluate(() => {
  const root = document.querySelector("[data-ff-sponsor-sales-flow]");
  const select = document.querySelector("[data-ff-sponsor-package-select]");
  const cta = document.querySelector("[data-ff-sponsor-continue]");
  const text = document.body.innerText.replace(/\s+/g, " ");

  if (select) {
    select.value = "season";
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }

  return {
    httpText: text.slice(0, 400),
    hasRoot: !!root,
    hasBusinessField: !!document.querySelector('[name="business_name"]'),
    hasEmailField: !!document.querySelector('[name="email"]'),
    hasRecognitionField: !!document.querySelector('[name="recognition_name"]'),
    hasPackageSelect: !!select,
    hasReviewCopy: /review|approved|recognition|before publishing/i.test(text),
    hasCheckoutTrigger: !!cta && cta.hasAttribute("data-ff-open-sponsor"),
    ctaText: cta ? cta.textContent.trim() : "",
    ctaAmount: cta ? cta.getAttribute("data-amount-cents") : "",
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2
  };
});

await browser.close();

const checks = {
  page_ok: res && res.status() === 200,
  no_console_issues: issues.length === 0,
  sponsor_flow_present: data.hasRoot,
  business_field_present: data.hasBusinessField,
  email_field_present: data.hasEmailField,
  recognition_field_present: data.hasRecognitionField,
  package_select_present: data.hasPackageSelect,
  review_copy_present: data.hasReviewCopy,
  checkout_trigger_present: data.hasCheckoutTrigger,
  season_select_updates_amount: data.ctaAmount === "150000",
  no_horizontal_overflow: !data.overflow
};

const pass = Object.values(checks).every(Boolean);

const report = {
  generatedAt: new Date().toISOString(),
  pass,
  checks,
  issues,
  data,
  screenshot: path.relative(ROOT, screenshot)
};

const jsonPath = path.join(OUT, `ff_wave10a_sponsor_sales_scout_${stamp}.json`);
const mdPath = path.join(OUT, `ff_wave10a_sponsor_sales_scout_${stamp}.md`);

fs.writeFileSync(jsonPath, JSON.stringify(report, null, 2));

const lines = [
  "# FutureFunded Wave 10A Sponsor Sales Scout",
  "",
  `- **Generated:** \`${report.generatedAt}\``,
  `- **Status:** ${pass ? "✅ PASS" : "❌ REVIEW"}`,
  `- **Screenshot:** \`${report.screenshot}\``,
  "",
  "## Checks",
  "",
  "| Check | Result |",
  "| --- | --- |",
  ...Object.entries(checks).map(([k, v]) => `| \`${k}\` | ${v ? "✅" : "❌"} |`),
  "",
  "## CTA sync",
  "",
  `- CTA text: \`${data.ctaText}\``,
  `- CTA amount cents after selecting Season Sponsor: \`${data.ctaAmount}\``
];

if (issues.length) {
  lines.push("", "## Console/page issues", ...issues.map((x) => `- ${x}`));
}

fs.writeFileSync(mdPath, lines.join("\n"));

console.log(`✅ Wave 10A sponsor sales scout: ${mdPath}`);
console.log(`JSON: ${jsonPath}`);
console.log(`Status: ${pass ? "PASS" : "REVIEW"}`);
process.exit(pass ? 0 : 1);

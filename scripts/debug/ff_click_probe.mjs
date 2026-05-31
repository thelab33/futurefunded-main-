#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const out = path.join(root, "audit_outputs/live-debug/latest");
const url = "http://127.0.0.1:5000/c/connect-atx-elite";
const selector = process.argv.slice(2).join(" ") || "header [data-ff-open-checkout]";
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ headless: process.env.FF_HEADED !== "1", slowMo: Number(process.env.FF_SLOWMO || 0) });
const page = await browser.newPage({ viewport: { width: 390, height: 1400 }, isMobile: true, hasTouch: true });
page.setDefaultTimeout(5000);

const pageErrors = [];
const consoleRows = [];
const requestFailures = [];
const network = [];

page.on("pageerror", e => pageErrors.push(String(e.stack || e.message || e)));
page.on("console", m => consoleRows.push({ type: m.type(), text: m.text() }));
page.on("requestfailed", r => requestFailures.push({ method: r.method(), url: r.url(), failure: r.failure()?.errorText || "" }));
page.on("response", r => {
  if (/checkout|stripe|payment|session|donat|sponsor|\.(js|css)/i.test(r.url())) network.push({ status: r.status(), url: r.url() });
});

function state() {
  const clean = v => String(v || "").replace(/\s+/g, " ").trim();
  const visible = el => {
    if (!el) return false;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return cs.display !== "none" && cs.visibility !== "hidden" && Number(cs.opacity || 1) > 0 && r.width > 10 && r.height > 10;
  };
  const checkout = document.querySelector("#checkout,[data-ff-checkout-sheet],[data-ff-embedded-checkout-shell]");
  const dialogs = Array.from(document.querySelectorAll("[role='dialog'],#checkout,[data-ff-checkout-sheet],[data-ff-sponsor-modal],.ff-modal,.ff-checkoutModal"))
    .filter(visible)
    .map(el => ({ id: el.id || "", className: String(el.className || ""), hidden: el.hidden, aria: el.getAttribute("aria-hidden"), state: el.getAttribute("data-ff-state") || el.getAttribute("data-ff-checkout-state") || "", text: clean(el.textContent).slice(0, 120) }));
  return {
    htmlClass: document.documentElement.className,
    bodyClass: document.body?.className || "",
    checkout: checkout ? { found: true, hidden: checkout.hidden, aria: checkout.getAttribute("aria-hidden"), state: checkout.getAttribute("data-ff-state"), checkoutState: checkout.getAttribute("data-ff-checkout-state"), visible: visible(checkout), className: String(checkout.className || "") } : { found: false },
    dialogs
  };
}

function inspect(sel) {
  const clean = v => String(v || "").replace(/\s+/g, " ").trim();
  const pathFor = el => {
    if (!el) return "";
    const parts = [];
    let n = el;
    while (n && n.nodeType === 1 && parts.length < 6) {
      let p = n.tagName.toLowerCase();
      if (n.id) p += "#" + n.id;
      const cls = String(n.className || "").split(/\s+/).filter(Boolean).slice(0,3);
      if (cls.length) p += "." + cls.join(".");
      parts.unshift(p);
      n = n.parentElement;
    }
    return parts.join(" > ");
  };
  const el = document.querySelector(sel);
  if (!el) return { found: false, selector: sel };
  const r = el.getBoundingClientRect();
  const x = Math.max(0, Math.min(innerWidth - 1, Math.round(r.left + r.width / 2)));
  const y = Math.max(0, Math.min(innerHeight - 1, Math.round(r.top + r.height / 2)));
  const top = document.elementFromPoint(x, y);
  return {
    found: true,
    selector: sel,
    path: pathFor(el),
    text: clean(el.innerText || el.value || el.getAttribute("aria-label")),
    data: Object.fromEntries(Array.from(el.attributes || []).filter(a => a.name.startsWith("data-ff")).map(a => [a.name, a.value])),
    rect: { x: r.x, y: r.y, width: r.width, height: r.height },
    covered: !(top === el || el.contains(top)),
    topPath: pathFor(top),
    topText: clean(top?.innerText || top?.value || top?.getAttribute?.("aria-label")).slice(0, 120)
  };
}

let status = null;
let gotoError = "";
let before = null;
let trialError = "";
let clickError = "";
let after = null;

try {
  const res = await page.goto(`${url}?ff_click=${Date.now()}`, { waitUntil: "domcontentloaded", timeout: 30000 });
  status = res?.status() || null;
  await page.waitForTimeout(800);

  const loc = page.locator(selector).first();
  await loc.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);

  before = await page.evaluate(inspect, selector);

  try { await loc.click({ trial: true, timeout: 4000 }); } catch (e) { trialError = String(e.message || e); }
  try { await loc.click({ timeout: 5000 }); await page.waitForTimeout(900); } catch (e) { clickError = String(e.message || e); }

  after = await page.evaluate(state);
} catch (e) {
  gotoError = String(e.message || e);
  try { after = await page.evaluate(state); } catch {}
}

await page.screenshot({ path: path.join(out, "click-trace.png"), fullPage: true }).catch(() => {});
await browser.close().catch(() => {});

const result = { selector, status, gotoError, before, trialError, clickError, after, pageErrors, consoleRows, requestFailures, network };
fs.writeFileSync(path.join(out, "click-trace.json"), JSON.stringify(result, null, 2));

const md = [
  "# FutureFunded Click Trace",
  "",
  `Selector: \`${selector}\``,
  `Status: ${status}`,
  "",
  "## Target",
  `- found: ${before?.found}`,
  `- text: "${before?.text || ""}"`,
  `- path: \`${before?.path || ""}\``,
  `- covered: ${before?.covered ? "YES" : "no"}`,
  before?.covered ? `  - top: \`${before.topPath}\`` : "",
  before?.covered ? `  - top text: "${before.topText}"` : "",
  `- trial error: ${trialError ? "YES" : "no"}`,
  trialError ? `  - ${trialError.split("\n")[0]}` : "",
  `- click error: ${clickError ? "YES" : "no"}`,
  clickError ? `  - ${clickError.split("\n")[0]}` : "",
  "",
  "## Checkout after click",
  `- found: ${after?.checkout?.found}`,
  `- visible: ${after?.checkout?.visible}`,
  `- hidden: ${after?.checkout?.hidden}`,
  `- aria-hidden: ${after?.checkout?.aria}`,
  `- state: ${after?.checkout?.state || after?.checkout?.checkoutState || ""}`,
  `- dialogs visible: ${after?.dialogs?.length || 0}`,
  "",
  "## Page errors",
  pageErrors.length ? pageErrors.map(e => `- ${e.split("\n")[0]}`).join("\n") : "- none",
  "",
  "## Request failures",
  requestFailures.length ? requestFailures.map(e => `- ${e.method} ${e.url} — ${e.failure}`).join("\n") : "- none",
  "",
  "## Network",
  ...network.slice(-25).map(r => `- ${r.status} ${r.url}`)
].filter(Boolean).join("\n");

fs.writeFileSync(path.join(out, "click-trace.md"), md);
console.log(md);

#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const ROOT = process.cwd();
const BASE = process.env.FF_VISUAL_BASE || "http://127.0.0.1:5000";

function readToken() {
  if (process.env.FF_OPERATOR_ACCESS_TOKEN) return process.env.FF_OPERATOR_ACCESS_TOKEN;
  try { return fs.readFileSync("/tmp/ff_operator_token", "utf8").trim(); }
  catch { return ""; }
}

const token = readToken();
const dashboardUrl = token
  ? `${BASE}/platform/dashboard?token=${encodeURIComponent(token)}`
  : `${BASE}/platform/dashboard`;

const surfaces = [
  ["Platform desktop", `${BASE}/platform/`, 1180, 980, 0, 0],
  ["Campaign desktop", `${BASE}/c/connect-atx-elite`, 1180, 980, 1220, 0],
  ["Onboarding desktop", `${BASE}/platform/onboarding`, 1180, 980, 2440, 0],
  ["Dashboard desktop", dashboardUrl, 1180, 980, 3660, 0],
  ["Login desktop", `${BASE}/platform/login`, 1180, 980, 4880, 0],
  ["Platform mobile", `${BASE}/platform/`, 420, 980, 0, 1040],
  ["Campaign mobile", `${BASE}/c/connect-atx-elite`, 420, 980, 460, 1040],
  ["Onboarding mobile", `${BASE}/platform/onboarding`, 420, 980, 920, 1040],
  ["Dashboard mobile", dashboardUrl, 420, 980, 1380, 1040],
  ["Login mobile", `${BASE}/platform/login`, 420, 980, 1840, 1040],
];

const userDataRoot = path.join(ROOT, ".tmp_live_surface_wall");
fs.rmSync(userDataRoot, { recursive: true, force: true });
fs.mkdirSync(userDataRoot, { recursive: true });

console.log("");
console.log("FutureFunded Live Surface Wall");
console.log("==============================");
console.log(`Base: ${BASE}`);
console.log(`Private dashboard token: ${token ? "loaded" : "missing - locked dashboard will open"}`);
console.log("");

const contexts = [];

for (const [name, url, width, height, x, y] of surfaces) {
  const profileDir = path.join(userDataRoot, name.toLowerCase().replace(/[^a-z0-9]+/g, "-"));
  const context = await chromium.launchPersistentContext(profileDir, {
    headless: false,
    viewport: { width, height },
    deviceScaleFactor: 1,
    args: ["--no-sandbox", `--window-size=${width},${height}`, `--window-position=${x},${y}`, "--disable-infobars"],
  });
  const page = context.pages()[0] || await context.newPage();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 }).catch((error) => {
    console.error(`Could not load ${name}: ${error.message}`);
  });
  await page.evaluate((title) => { document.title = title; }, `FF · ${name}`).catch(() => {});
  contexts.push(context);
  console.log(`OPEN ${name}`);
  console.log(`  ${url.replace(/token=[^&]+/i, "token=REDACTED")}`);
}

console.log("");
console.log("Live wall is open.");
console.log("Refresh these windows after each CSS asset restart.");
console.log("Press Ctrl+C here to close all wall browsers.");
console.log("");

async function shutdown() {
  for (const context of contexts) await context.close().catch(() => {});
  fs.rmSync(userDataRoot, { recursive: true, force: true });
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
await new Promise(() => {});

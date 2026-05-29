#!/usr/bin/env node

import { chromium } from "playwright";

const base =
  process.env.FF_QA_BASE_URL ||
  process.argv.find((arg) => /^https?:\/\//.test(arg)) ||
  "http://127.0.0.1:5000";

const pages = [
  {
    name: "homepage",
    url: `${base}/platform/`,
    h1MustContain: "Launch fundraising pages donors trust",
    maxH1Height: 390,
    maxHorizontalOverflow: 4,
  },
  {
    name: "campaign",
    url: `${base}/c/connect-atx-elite?mode=preview`,
    h1MustContain: "Fuel the season",
    maxH1Height: 310,
    maxHorizontalOverflow: 4,
  },
];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 960 } });

const failures = [];
const passes = [];

function pass(name, detail = "") {
  passes.push({ name, detail });
  console.log(`OK ${name}${detail ? ` - ${detail}` : ""}`);
}

function fail(name, detail = "") {
  failures.push({ name, detail });
  console.log(`FAIL ${name}${detail ? ` - ${detail}` : ""}`);
}

for (const item of pages) {
  try {
    const response = await page.goto(item.url, { waitUntil: "domcontentloaded", timeout: 30000 });
    const status = response?.status() || 0;

    if (status >= 200 && status < 400) pass(`${item.name} reachable`, String(status));
    else {
      fail(`${item.name} reachable`, `HTTP ${status}`);
      continue;
    }

    const h1 = page.locator("h1").first();
    const h1Text = (await h1.textContent())?.replace(/\s+/g, " ").trim() || "";
    if (h1Text.includes(item.h1MustContain)) {
      pass(`${item.name} h1 copy`, h1Text.slice(0, 70));
    } else {
      fail(`${item.name} h1 copy`, h1Text);
    }

    const h1Box = await h1.boundingBox();
    if (h1Box && h1Box.height <= item.maxH1Height) {
      pass(`${item.name} h1 mobile height`, `${Math.round(h1Box.height)}px`);
    } else {
      fail(`${item.name} h1 mobile height`, `${Math.round(h1Box?.height || 0)}px`);
    }

    const overflow = await page.evaluate(() => {
      return Math.max(0, document.documentElement.scrollWidth - window.innerWidth);
    });

    if (overflow <= item.maxHorizontalOverflow) {
      pass(`${item.name} no horizontal overflow`, `${overflow}px`);
    } else {
      fail(`${item.name} no horizontal overflow`, `${overflow}px`);
    }

    const cssLinked = await page.locator('link[href*="ff.campaign-polish.css"]').count();
    if (cssLinked > 0) pass(`${item.name} campaign polish CSS linked`);
    else fail(`${item.name} campaign polish CSS linked`, "missing");
  } catch (error) {
    fail(`${item.name} visual rhythm runtime`, error?.message || String(error));
  }
}

await browser.close();

console.log("");
console.log("=== VISUAL RHYTHM QA SUMMARY ===");
console.log(`Passed: ${passes.length}`);
console.log(`Failed: ${failures.length}`);

if (failures.length) {
  console.log("");
  console.log("Failures:");
  for (const item of failures) console.log(`- ${item.name}: ${item.detail}`);
  process.exitCode = 1;
}

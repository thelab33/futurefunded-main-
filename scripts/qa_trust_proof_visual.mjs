#!/usr/bin/env node

import { chromium } from "playwright";

const base =
  process.env.FF_QA_BASE_URL ||
  process.argv.find((arg) => /^https?:\/\//.test(arg)) ||
  "http://127.0.0.1:5000";

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

try {
  await page.goto(`${base}/platform/`, { waitUntil: "domcontentloaded", timeout: 30000 });

  const disclosure = page.locator("[data-ff-demo-metric-disclosure]").first();
  if ((await disclosure.count()) > 0 && (await disclosure.isVisible())) {
    const text = (await disclosure.textContent())?.replace(/\s+/g, " ").trim() || "";
    const box = await disclosure.boundingBox();
    if (text.length <= 72) pass("homepage disclosure compact", text);
    else fail("homepage disclosure compact", `${text.length} chars: ${text}`);

    if (box && box.height <= 46) pass("homepage disclosure height", `${Math.round(box.height)}px`);
    else fail("homepage disclosure height", `${Math.round(box?.height || 0)}px`);
  } else {
    fail("homepage disclosure visible", "missing");
  }

  await page.goto(`${base}/c/connect-atx-elite?mode=preview`, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  const proof = page.locator("[data-ff-recent-ledger-proof]").first();
  if ((await proof.count()) > 0 && (await proof.isVisible())) {
    pass("ledger proof visible");

    const box = await proof.boundingBox();
    if (box && box.width >= 260) pass("ledger proof usable width", `${Math.round(box.width)}px`);
    else fail("ledger proof usable width", `${Math.round(box?.width || 0)}px`);

    if (box && box.height <= 118)
      pass("ledger proof compact height", `${Math.round(box.height)}px`);
    else fail("ledger proof compact height", `${Math.round(box?.height || 0)}px`);

    const text = (await proof.textContent())?.replace(/\s+/g, " ").trim() || "";
    if (text.includes("Recent campaign activity")) pass("ledger proof copy");
    else fail("ledger proof copy", text);
  } else {
    fail("ledger proof visible", "missing");
  }

  const sponsorNote = page.locator("[data-ff-sponsor-review-note]").first();
  if ((await sponsorNote.count()) > 0) {
    const box = await sponsorNote.boundingBox();
    if (box && box.height <= 92) pass("sponsor review note compact", `${Math.round(box.height)}px`);
    else fail("sponsor review note compact", `${Math.round(box?.height || 0)}px`);
  } else {
    fail("sponsor review note present", "missing");
  }
} catch (error) {
  fail("trust proof visual runtime", error?.message || String(error));
} finally {
  await browser.close();
}

console.log("");
console.log("=== TRUST PROOF VISUAL QA SUMMARY ===");
console.log(`Passed: ${passes.length}`);
console.log(`Failed: ${failures.length}`);

if (failures.length) {
  console.log("");
  console.log("Failures:");
  for (const item of failures) console.log(`- ${item.name}: ${item.detail}`);
  process.exitCode = 1;
}

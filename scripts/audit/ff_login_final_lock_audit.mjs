#!/usr/bin/env node
import { chromium } from "playwright";

const base = process.argv[2] || "http://127.0.0.1:5000";
const url = `${base.replace(/\/$/, "")}/platform/login?login_final_lock=1`;
const checks = [];

function record(ok, label, detail = "") {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
}

const browser = await chromium.launch({ headless: true });

for (const viewport of [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 390, height: 1100 },
]) {
  console.log(`\nFutureFunded login final lock audit [${viewport.name}]`);

  const page = await browser.newPage({ viewport });
  const res = await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  const status = res?.status() || 0;
  const html = await page.content();

  record(status === 200, "Login responds", `status=${status}`);
  record(html.includes("ff.css"), "Login loads ff.css");
  record(!html.includes("ff.cinematic.css"), "Login does not load cinematic CSS");
  record(!html.includes("ff-cinematic.js"), "Login does not load cinematic JS");
  record(html.includes("data-ff-login-contract") || html.includes("ff-loginCommandBody"), "Login contract present");
  record(html.includes("FutureFunded"), "FutureFunded brand copy present");

  const metrics = await page.evaluate(() => {
    const root = document.documentElement;
    const brand = document.querySelector(".ff-loginStandalone__brand, .ff-loginBrand, .ff-platformBrand, [aria-label*='FutureFunded']");
    const mark = document.querySelector(".ff-loginStandalone__brandMark, .ff-loginBrand__mark, .ff-platformBrand__mark");
    const shell = document.querySelector(".ff-loginStandalone__shell, .ff-loginGrid, .ff-loginShell, main");
    const form = document.querySelector("form");
    const card = document.querySelector(".ff-loginStandalone__card, .ff-loginCard, .ff-loginPanel, form");
    const brandRect = brand?.getBoundingClientRect();
    const markRect = mark?.getBoundingClientRect();
    const shellRect = shell?.getBoundingClientRect();
    const cardRect = card?.getBoundingClientRect();

    return {
      overflowX: root.scrollWidth > root.clientWidth + 2,
      scrollHeight: root.scrollHeight,
      brandText: brand?.textContent?.replace(/\s+/g, " ").trim() || "",
      markText: mark?.textContent?.replace(/\s+/g, " ").trim() || "",
      brandVisible: !!(brandRect && brandRect.width > 40 && brandRect.height > 20),
      markVisible: !!(markRect && markRect.width >= 30 && markRect.height >= 30),
      shellVisible: !!(shellRect && shellRect.width > 220 && shellRect.height > 240),
      cardVisible: !!(cardRect && cardRect.width > 220 && cardRect.height > 120),
      formPresent: !!form,
      actions: document.querySelectorAll("button, a[href]").length,
    };
  });

  record(!metrics.overflowX, "Login has no horizontal overflow");
  record(metrics.brandVisible, "Login brand visible", metrics.brandText);
  record(/FutureFunded/i.test(metrics.brandText), "Login brand title says FutureFunded", metrics.brandText);
  record(metrics.markVisible, "Login brand mark visible", metrics.markText || "visual mark");
  record(metrics.markText === "" || /FF/i.test(metrics.markText), "Login brand mark canonical", metrics.markText || "visual/asset mark");
  record(metrics.shellVisible, "Login shell visible", `height=${metrics.scrollHeight}`);
  record(metrics.cardVisible || metrics.formPresent, "Login auth panel/form visible");
  record(metrics.actions >= 2, "Login has action surface", `actions=${metrics.actions}`);

  await page.close();
}

await browser.close();

const failed = checks.filter((x) => !x.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) process.exit(1);

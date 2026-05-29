#!/usr/bin/env node
import { chromium } from "playwright";

const base = process.argv[2] || "http://127.0.0.1:5000";
const url = `${base.replace(/\/$/, "")}/platform/login?login_audit=1`;

const checks = [];
const record = (ok, label, detail = "") => {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
};

const browser = await chromium.launch({ headless: true });

for (const viewport of [
  { name: "desktop", width: 1440, height: 1200 },
  { name: "mobile", width: 390, height: 1200 },
]) {
  console.log(`\nFutureFunded login command audit [${viewport.name}]`);
  const page = await browser.newPage({ viewport });
  const response = await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  const status = response?.status() || 0;
  const html = await page.content();

  record(status === 200, "Login responds", `status=${status}`);
  record(html.includes("ff.css"), "Login loads ff.css");
  record(!html.includes("ff.cinematic.css"), "Login does not load cinematic CSS");
  record(!html.includes("ff-cinematic.js"), "Login does not load cinematic JS");
  record(html.includes("FutureFunded"), "FutureFunded brand text present");
  record(html.includes("ff-loginCommandBody") || html.includes("ff-loginStandaloneBody"), "Login command body class present");

  const metrics = await page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const brand = document.querySelector(
      ".ff-loginStandalone__brand, .ff-loginBrand, .ff-platformBrand, [aria-label*='FutureFunded']"
    );
    const mark = document.querySelector(
      ".ff-loginStandalone__brandMark, .ff-loginBrand__mark, .ff-platformBrand__mark"
    );
    const shell = document.querySelector(".ff-loginStandalone__shell, .ff-loginGrid, .ff-loginShell");
    const card = document.querySelector(".ff-loginStandalone__card, .ff-loginCard, .ff-loginPanel, form");
    const form = document.querySelector("form");
    const inputs = document.querySelectorAll("input").length;
    const buttons = document.querySelectorAll("button, .ff-button, a[href]").length;
    const brandRect = brand?.getBoundingClientRect();
    const markRect = mark?.getBoundingClientRect();
    const shellRect = shell?.getBoundingClientRect();
    const cardRect = card?.getBoundingClientRect();

    const paintBlocked = [shell, card].filter(Boolean).map((node) => {
      const cs = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return {
        cls: node.className || node.tagName,
        opacity: Number.parseFloat(cs.opacity || "1"),
        visibility: cs.visibility,
        contentVisibility: cs.contentVisibility,
        height: Math.round(rect.height),
      };
    }).filter((item) =>
      item.visibility === "hidden" ||
      item.opacity < 0.98 ||
      item.contentVisibility === "auto" ||
      item.height < 20
    );

    return {
      bodyClass: body.className,
      overflowX: root.scrollWidth > root.clientWidth + 2,
      scrollHeight: root.scrollHeight,
      brandText: brand?.textContent?.replace(/\s+/g, " ").trim() || "",
      brandVisible: Boolean(brandRect && brandRect.width > 40 && brandRect.height > 20),
      markText: mark?.textContent?.replace(/\s+/g, " ").trim() || "",
      markVisible: Boolean(markRect && markRect.width >= 30 && markRect.height >= 30),
      shellVisible: Boolean(shellRect && shellRect.width > 200 && shellRect.height > 200),
      cardVisible: Boolean(cardRect && cardRect.width > 200 && cardRect.height > 120),
      formPresent: Boolean(form),
      inputs,
      buttons,
      paintBlocked,
    };
  });

  record(!metrics.overflowX, "Login has no horizontal overflow");
  record(metrics.brandVisible, "Login platform brand is visible", metrics.brandText);
  record(/FutureFunded/i.test(metrics.brandText), "Login brand title says FutureFunded", metrics.brandText);
  record(metrics.markVisible, "Login brand mark is visible", metrics.markText || "visual mark");
  record(metrics.markText === "" || /FF/i.test(metrics.markText), "Login brand mark is canonical", metrics.markText || "visual/asset mark");
  record(metrics.shellVisible || metrics.cardVisible, "Login layout shell/card visible");
  record(metrics.formPresent || metrics.buttons >= 3, "Login has auth action surface", `inputs=${metrics.inputs} actions=${metrics.buttons}`);
  record(metrics.paintBlocked.length === 0, "Login sections are paint-ready",
    metrics.paintBlocked.map((x) => `${x.cls}:${x.contentVisibility}:${x.opacity}:${x.visibility}:${x.height}`).join(" | ")
  );

  await page.close();
}

await browser.close();

const failed = checks.filter((x) => !x.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) process.exit(1);

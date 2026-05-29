#!/usr/bin/env node
import { chromium } from "playwright";

const base = process.argv[2] || "http://127.0.0.1:5000";
const url = `${base.replace(/\/$/, "")}/platform/login?login_v4_audit=1`;
const checks = [];

function record(ok, label, detail = "") {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
}

const browser = await chromium.launch({ headless: true });

for (const viewport of [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 390, height: 1200 },
]) {
  console.log(`\nFutureFunded login V4 isolated audit [${viewport.name}]`);

  const page = await browser.newPage({ viewport });
  const res = await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  const status = res?.status() || 0;
  const html = await page.content();

  record(status === 200, "Login responds", `status=${status}`);
  record(html.includes("ff.css"), "Login loads ff.css");
  record(!html.includes("ff.cinematic.css"), "Login does not load cinematic CSS");
  record(!html.includes("ff-cinematic.js"), "Login does not load cinematic JS");
  record(html.includes('data-ff-login-contract="operator-login-v4"'), "Login V4 contract present");
  record(html.includes("FutureFunded"), "FutureFunded brand copy present");
  record(!html.includes("ff-loginStandalone__"), "Legacy standalone selectors removed from template");

  const metrics = await page.evaluate((viewportName) => {
    const root = document.documentElement;
    const topbar = document.querySelector(".ff-loginV4__topbar");
    const stage = document.querySelector(".ff-loginV4__stage");
    const hero = document.querySelector(".ff-loginV4__hero");
    const card = document.querySelector(".ff-loginV4__card");
    const footer = document.querySelector(".ff-loginV4__footer");
    const brandMarks = document.querySelectorAll(".ff-loginV4__brandMark").length;

    const r = (node) => node ? node.getBoundingClientRect() : null;
    const tr = r(topbar);
    const sr = r(stage);
    const hr = r(hero);
    const cr = r(card);
    const fr = r(footer);

    const desktopNoOverlap = viewportName === "desktop"
      ? Boolean(hr && cr && cr.left >= hr.right - 2)
      : true;

    const mobileOrderOk = viewportName === "mobile"
      ? Boolean(hr && cr && hr.top >= cr.bottom - 2)
      : true;

    return {
      overflowX: root.scrollWidth > root.clientWidth + 2,
      scrollHeight: root.scrollHeight,
      headerGap: tr && sr ? Math.round(sr.top - tr.bottom) : null,
      brandMarks,
      brandText: document.querySelector(".ff-loginV4__brand")?.textContent?.replace(/\s+/g, " ").trim() || "",
      heroVisible: Boolean(hr && hr.width > 260 && hr.height > 180),
      cardVisible: Boolean(cr && cr.width > 260 && cr.height > 360),
      footerVisible: Boolean(fr && fr.width > 260 && fr.height > 40),
      desktopNoOverlap,
      mobileOrderOk,
      cardTopText: card?.textContent?.replace(/\s+/g, " ").trim().slice(0, 80) || "",
    };
  }, viewport.name);

  record(!metrics.overflowX, "Login has no horizontal overflow");
  record(metrics.brandMarks === 1, "Login has exactly one brand mark", `count=${metrics.brandMarks}`);
  record(/FutureFunded/i.test(metrics.brandText), "Login brand title says FutureFunded", metrics.brandText);
  record(metrics.heroVisible, "Login hero panel is visible", `height=${metrics.scrollHeight}`);
  record(metrics.cardVisible, "Login auth card is visible", metrics.cardTopText);
  record(metrics.desktopNoOverlap, "Desktop hero/card do not overlap");
  record(metrics.mobileOrderOk, "Mobile card/hero order is intentional");
  record(metrics.footerVisible, "Login footer is visible");
  record(metrics.headerGap !== null && metrics.headerGap >= 8 && metrics.headerGap <= 28, "Header-to-stage rhythm is tight", `gap=${metrics.headerGap}`);
  record(metrics.scrollHeight <= (viewport.name === "desktop" ? 1300 : 2300), "Login page height is controlled", `height=${metrics.scrollHeight}`);

  await page.close();
}

await browser.close();

const failed = checks.filter((x) => !x.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) process.exit(1);

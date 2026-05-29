#!/usr/bin/env node
import { chromium } from "playwright";

const base = process.argv[2] || "http://127.0.0.1:5000";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || "";
const results = [];

function record(ok, label, detail = "") {
  results.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
}

async function inspect(page, url, label, expectPrivate = false) {
  const res = await page.goto(url, { waitUntil: "networkidle", timeout: 60000 }).catch(() => null);
  const status = res?.status?.() ?? 0;
  const html = await page.content();

  record(status > 0 && status < 500, `${label} responds`, `status=${status}`);
  record(html.includes("ff.css"), `${label} loads ff.css`);
  record(!html.includes("ff.cinematic.css"), `${label} does not load cinematic CSS`);
  record(!html.includes("ff-cinematic.js"), `${label} does not load cinematic JS`);

  const metrics = await page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const topbar = document.querySelector(".ff-dashboardModern__topbar")?.getBoundingClientRect();
    const hero = document.querySelector(".ff-dashboardModern__hero")?.getBoundingClientRect();
    const kpis = document.querySelector(".ff-dashboardModern__kpis")?.getBoundingClientRect();
    const panels = [...document.querySelectorAll(".ff-dashboardModern__panel, .ff-dashboardModern__sidebarCard, .ff-dashboardLocked")];
    return {
      overflowX: root.scrollWidth > root.clientWidth + 2,
      height: root.scrollHeight,
      bodyClass: body.className,
      topbar: Boolean(topbar),
      hero: Boolean(hero),
      kpis: Boolean(kpis),
      panelCount: panels.length,
      headerToHeroGap: topbar && hero ? Math.round(hero.top - topbar.bottom) : null,
    };
  });

  record(metrics.overflowX === false, `${label} has no horizontal overflow`);
  if (expectPrivate) {
    record(metrics.bodyClass.includes("ff-dashboardModernBody"), `${label} modern dashboard body class present`);
    record(metrics.topbar, `${label} modern topbar detected`);
    record(metrics.hero, `${label} modern hero detected`);
    record(metrics.kpis, `${label} KPI row detected`);
    record(metrics.panelCount >= 3, `${label} command panels detected`, `count=${metrics.panelCount}`);
    record(metrics.headerToHeroGap !== null && metrics.headerToHeroGap <= 28, `${label} header-to-hero rhythm is tight`, `gap=${metrics.headerToHeroGap}`);
  } else {
    record(html.includes("Operator access required") || html.includes("Protected workspace"), `${label} protected state copy detected`);
  }
}

const browser = await chromium.launch({ headless: true });

for (const viewport of [
  { name: "desktop", width: 1440, height: 1200 },
  { name: "mobile", width: 390, height: 1400 },
]) {
  console.log(`\nFutureFunded dashboard command audit [${viewport.name}]`);
  const page = await browser.newPage({ viewport });

  await inspect(page, `${base}/platform/dashboard`, `Dashboard locked ${viewport.name}`, false);

  if (token) {
    let privateUrl = `${base}/platform/dashboard?token=${encodeURIComponent(token)}`;
    await inspect(page, privateUrl, `Dashboard private ${viewport.name}`, true);
  } else {
    console.log("INFO FF_OPERATOR_ACCESS_TOKEN not set; private dashboard visual check skipped.");
  }

  await page.close();
}

await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\nSummary: ${results.length - failed.length}/${results.length} passed`);
if (failed.length) process.exit(1);

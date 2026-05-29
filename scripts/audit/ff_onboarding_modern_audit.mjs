#!/usr/bin/env node
import { chromium } from "playwright";

const base = process.argv[2] || "http://127.0.0.1:5000";
const url = `${base.replace(/\/$/, "")}/platform/onboarding?onboarding_audit=1`;

const checks = [];
const record = (ok, label, detail = "") => {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
};

const browser = await chromium.launch({ headless: true });

for (const viewport of [
  { name: "desktop", width: 1440, height: 1400 },
  { name: "mobile", width: 390, height: 1200 },
]) {
  const page = await browser.newPage({ viewport });
  const response = await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  const status = response?.status() || 0;
  const html = await page.content();

  console.log(`\nFutureFunded onboarding modern audit [${viewport.name}]`);
  record(status === 200, "Onboarding responds", `status=${status}`);
  record(html.includes("ff.css"), "Onboarding loads ff.css");
  record(!html.includes("ff.cinematic.css"), "Onboarding does not load cinematic CSS");
  record(!html.includes("ff-cinematic.js"), "Onboarding does not load cinematic JS");
  record(html.includes("ff-onboardModernBody"), "Modern onboarding body class present");
  record(html.includes("data-ff-contract=\"operator-launch-setup\""), "Launch setup contract present");
  record(html.includes("data-ff-contract=\"operator-launch-setup-save\""), "Save contract present");

  const metrics = await page.evaluate(() => {
    const root = document.documentElement;
    const sections = Array.from(document.querySelectorAll(
      ".ff-onboardModernHero, .ff-onboardModernSteps, .ff-onboardModernCommand, .ff-onboardModernSetup, .ff-onboardModernKit, .ff-onboardModernHandoff"
    ));
    const inputs = document.querySelectorAll("input, select, textarea").length;
    const ctas = document.querySelectorAll(".ff-button, button, a[href]").length;

    const paintBlocked = sections.map((node) => {
      const cs = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return {
        className: node.className || node.tagName,
        opacity: Number.parseFloat(cs.opacity || "1"),
        visibility: cs.visibility,
        display: cs.display,
        contentVisibility: cs.contentVisibility,
        height: Math.round(rect.height),
      };
    }).filter((item) =>
      item.display === "none" ||
      item.visibility === "hidden" ||
      item.opacity < 0.98 ||
      item.contentVisibility === "auto" ||
      item.height < 20
    );

    return {
      scrollHeight: root.scrollHeight,
      overflowX: root.scrollWidth > root.clientWidth + 2,
      sectionCount: sections.length,
      inputs,
      ctas,
      paintBlocked,
    };
  });

  record(!metrics.overflowX, "Onboarding has no horizontal overflow");
  record(metrics.sectionCount >= 6, "Onboarding sections detected", `count=${metrics.sectionCount}`);
  record(metrics.inputs >= 10, "Onboarding form fields detected", `count=${metrics.inputs}`);
  record(metrics.ctas >= 8, "Onboarding has enough navigation/actions", `count=${metrics.ctas}`);
  record(metrics.scrollHeight > viewport.height * 1.8, "Onboarding has top-to-bottom content", `height=${metrics.scrollHeight}`);
  record(metrics.paintBlocked.length === 0, "Onboarding sections are paint-ready",
    metrics.paintBlocked.slice(0, 4).map((x) => `${x.className}:${x.contentVisibility}:${x.opacity}:${x.visibility}:${x.height}`).join(" | ")
  );

  await page.close();
}

await browser.close();

const failed = checks.filter((c) => !c.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) process.exit(1);

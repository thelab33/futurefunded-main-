#!/usr/bin/env node
import { chromium } from "playwright";

const base = process.argv[2] || "http://127.0.0.1:5000";
const url = `${base.replace(/\/$/, "")}/platform/?home_audit=1`;

const checks = [];
const record = (ok, label, detail = "") => {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
};

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });

const response = await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
const status = response?.status() || 0;
record(status === 200, "Homepage responds", `status=${status}`);

const html = await page.content();

record(html.includes('data-ff-page="platform-home"'), "Homepage data contract is present");
record(html.includes("platform-home.css"), "Homepage CSS asset is linked");
record(html.includes("ff.css"), "Shared ff.css asset is linked");
record(!html.includes("ff.cinematic.css"), "Homepage does not load cinematic CSS");
record(!html.includes("ff-cinematic.js"), "Homepage does not load cinematic JS");

for (const anchor of ["#product", "#demo", "#sponsors", "#launch", "#faq"]) {
  record(html.includes(`href="${anchor}"`) || html.includes(`href='${anchor}'`), `Homepage nav anchor ${anchor} is present`);
}

for (const text of [
  "Fundraising pages",
  "Campaign readiness",
  "One polished path",
  "One launch system",
  "Sponsor packages",
  "Show a campaign"
]) {
  record(html.toLowerCase().includes(text.toLowerCase()), `Homepage copy marker "${text}" is present`);
}

const metrics = await page.evaluate(() => {
  const doc = document.documentElement;
  const body = document.body;
  const sections = Array.from(document.querySelectorAll(".ff-homeSection, .ff-platformSection, section"));
  const root = document.querySelector("[data-ff-home-root], .ff-home, .ff-platformPage");
  const hero = document.querySelector(".ff-homeHero, .ff-platformHero, [data-ff-home-hero]");
  const ctas = document.querySelectorAll("[data-ff-home-cta], [data-ff-home-demo-cta], .ff-button");
  return {
    overflowX: doc.scrollWidth > doc.clientWidth + 2,
    scrollHeight: Math.max(doc.scrollHeight, body?.scrollHeight || 0),
    viewportHeight: window.innerHeight,
    sectionCount: sections.length,
    hasRoot: Boolean(root),
    hasHero: Boolean(hero),
    ctaCount: ctas.length,
  };
});

record(!metrics.overflowX, "Homepage has no horizontal overflow");
record(metrics.hasRoot, "Homepage root detected");
record(metrics.sectionCount >= 5, "Homepage has enough sections", `count=${metrics.sectionCount}`);
record(metrics.ctaCount >= 4, "Homepage has CTAs", `count=${metrics.ctaCount}`);
record(metrics.scrollHeight > metrics.viewportHeight * 1.6, "Homepage has top-to-bottom content", `height=${metrics.scrollHeight}`);

record(!html.includes("ff-cineReveal") && !html.includes("ff-cinematicReveal"), "Homepage reveal classes are absent");

const paintBlocked = await page.evaluate(() => {
  const nodes = Array.from(document.querySelectorAll(
    ".ff-platformCommandStrip, .ff-platformHomeSection, .ff-platformBento, .ff-platformDemoPanel, .ff-platformSponsorPanel, .ff-platformFaqPanel, .ff-platformFinalCard"
  ));

  return nodes
    .map((node) => {
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
    })
    .filter((item) =>
      item.display === "none" ||
      item.visibility === "hidden" ||
      item.opacity < 0.98 ||
      item.contentVisibility === "auto" ||
      item.height < 20
    );
});

record(paintBlocked.length === 0, "Homepage sections are paint-ready", paintBlocked.slice(0, 4).map((x) => `${x.className}:${x.contentVisibility}:${x.opacity}:${x.visibility}:${x.height}`).join(" | "));

record(!html.includes("Built for teams, schools, nonprofits, and clubs"), "Homepage removed duplicate audience block");
record(!html.includes("Launch with a real checklist, not a blank page."), "Homepage removed duplicate launch workflow block");
record(!html.includes("Ready to show without explaining the backend."), "Homepage removed founder demo proof block");

await browser.close();

const failed = checks.filter((c) => !c.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) process.exit(1);

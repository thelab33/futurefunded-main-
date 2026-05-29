#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const BASE = (process.env.FF_AUDIT_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || "";
const RUN = new Date().toISOString().replace(/[:.]/g, "-");
const OUT = path.join(process.cwd(), "audit_outputs", "premium-demo-readiness", RUN);
const LATEST = path.join(process.cwd(), "audit_outputs", "premium-demo-readiness", "latest");

fs.mkdirSync(OUT, { recursive: true });

const surfaces = [
  {
    id: "platform",
    name: "Platform home",
    url: "/platform/",
    css: ["ff.css", "platform-home.css"],
    selectors: [
      "main",
      "a[href*='/platform/onboarding'], [data-ff-home-launch-cta], [data-ff-home-primary-cta]",
      "a[href*='/c/connect-atx-elite'], [data-ff-home-live-campaign-cta]",
      "nav a"
    ],
    public: true
  },
  {
    id: "campaign",
    name: "Campaign",
    url: "/c/connect-atx-elite",
    css: ["ff.css", "campaign.css"],
    selectors: [
      "main",
      "[data-ff-open-checkout], [data-ff-donate-trigger], [data-ff-payment-trigger]",
      "[data-ff-amount-button]",
      "[data-ff-custom-amount], input[name*='amount' i]",
      "[data-ff-share-trigger], [data-ff-qr-trigger]",
      "[data-ff-open-sponsor], [data-ff-sponsor-trigger]"
    ],
    public: true
  },
  {
    id: "login",
    name: "Login",
    url: "/platform/login",
    css: ["ff.css", "login.css"],
    selectors: [
      "main",
      "form",
      "input:not([type='hidden'])",
      "button, [type='submit']"
    ],
    public: false
  },
  {
    id: "onboarding",
    name: "Onboarding",
    url: "/platform/onboarding",
    css: ["ff.css", "onboarding.css"],
    selectors: [
      "main",
      "[data-ff-onboard-root]",
      "#launch-workspace-main",
      "a[href*='/c/connect-atx-elite']",
      "a[href*='/platform/dashboard'], a[href='#launch-setup'], button"
    ],
    public: false
  },
  {
    id: "dashboard_locked",
    name: "Dashboard locked",
    url: "/platform/dashboard",
    css: ["ff.css", "dashboard.css"],
    selectors: [
      "main",
      "[data-ff-dashboard-locked-root], [data-ff-surface='dashboard-locked'], .ff-dashboardLockedShell",
      "a[href*='/platform/login'], a[href*='/platform/']"
    ],
    public: false
  },
  {
    id: "dashboard_operator",
    name: "Dashboard operator",
    url: TOKEN ? `/platform/dashboard?access_token=${encodeURIComponent(TOKEN)}` : "",
    css: ["ff.css", "dashboard.css"],
    selectors: [
      "main",
      "[data-ff-operator-root], [data-ff-system-loop='platform-dashboard'], .ff-dashboardShell",
      "a[href*='/c/connect-atx-elite']",
      "a[href*='/platform/onboarding'], button, a[href*='ledger']"
    ],
    public: false,
    needsToken: true
  }
];

const badBase = [
  ["placeholder", /\bplaceholder\b/i],
  ["sample", /\bsample\b/i],
  ["coming_soon", /\bcoming\s+soon\b/i],
  ["lorem", /\blorem\s+ipsum\b/i],
  ["todo_fixme", /\bTODO\b|\bFIXME\b/i],
  ["debug", /\bdebug\b|\btraceback\b|\bstack trace\b/i],
  ["jinja_leak", /\{\{|\}\}|\{%|%\}/]
];

const badPublic = [
  ["demo", /\bdemo\b/i],
  ["test", /\btest\b/i]
];

function clean(s) {
  return String(s || "").replace(/\s+/g, " ").trim();
}

function flag(flags, level, code, msg, extra = null) {
  flags.push({ level, code, msg, extra });
}

async function auditOne(ctx, surface, viewport) {
  const flags = [];

  if (surface.needsToken && !TOKEN) {
    flag(flags, "warn", "missing_operator_token", "FF_OPERATOR_ACCESS_TOKEN is not set; authenticated dashboard audit skipped.");
    return { id: surface.id, name: surface.name, viewport, status: "WARN", flags, skipped: true };
  }

  const page = await ctx.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  page.on("console", m => {
    if (m.type() === "error" && !/favicon|ResizeObserver/i.test(m.text())) consoleErrors.push(m.text());
  });
  page.on("pageerror", e => pageErrors.push(e.message));

  const fullUrl = `${BASE}${surface.url}`;
  let httpStatus = 0;

  try {
    const res = await page.goto(fullUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    httpStatus = res?.status() || 0;
    await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  } catch (e) {
    flag(flags, "fail", "load_failed", e.message);
    await page.close();
    return { id: surface.id, name: surface.name, viewport, url: fullUrl, status: "FAIL", flags };
  }

  const data = await page.evaluate(({ surface, badBaseRaw, badPublicRaw }) => {
    const visible = el => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return cs.display !== "none" && cs.visibility !== "hidden" && r.width > 0 && r.height > 0;
    };

    const accName = el => {
      const labelledBy = el.getAttribute("aria-labelledby");
      if (labelledBy) {
        const txt = labelledBy.split(/\s+/).map(id => document.getElementById(id)?.textContent || "").join(" ").trim();
        if (txt) return txt;
      }
      if (el.getAttribute("aria-label")) return el.getAttribute("aria-label");
      if (el.id) {
        const lab = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (lab?.textContent?.trim()) return lab.textContent.trim();
      }
      const wrap = el.closest("label");
      if (wrap?.textContent?.trim()) return wrap.textContent.trim();
      return (el.textContent || el.placeholder || el.title || el.value || "").trim();
    };

    const text = document.body?.innerText || "";
    const html = document.documentElement.outerHTML || "";
    const hrefs = [...document.querySelectorAll("link[rel='stylesheet']")].map(x => x.href || x.getAttribute("href") || "");
    const selectorCounts = Object.fromEntries(surface.selectors.map(s => [s, document.querySelectorAll(s).length]));

    const bad = [];
    const scan = [...badBaseRaw];
    if (surface.public) scan.push(...badPublicRaw);

    for (const [name, src, fl] of scan) {
      const re = new RegExp(src, fl);
      const m = text.match(re);
      if (m) {
        const start = Math.max(0, m.index - 70);
        bad.push({ name, match: m[0], context: text.slice(start, start + 190).replace(/\s+/g, " ").trim() });
      }
    }

    if (/\{\{|\}\}|\{%|%\}/.test(html)) bad.push({ name: "rendered_template_leak", match: "template marker", context: "Rendered HTML contains Jinja markers." });

    const controls = [...document.querySelectorAll("a[href],button,input:not([type='hidden']),select,textarea,summary,[role='button']")].filter(visible);
    const unnamed = controls
      .filter(el => !accName(el))
      .slice(0, 12)
      .map(el => ({
        tag: el.tagName.toLowerCase(),
        cls: String(el.className || "").slice(0, 80),
        id: el.id || "",
        href: el.getAttribute("href") || "",
        type: el.getAttribute("type") || ""
      }));

    const overflowX = Math.max(0, document.documentElement.scrollWidth - innerWidth, document.body.scrollWidth - innerWidth);

    const headers = [...document.querySelectorAll("header,[data-ff-header],.ff-campaignHeader")].filter(visible).map(el => {
      const r = el.getBoundingClientRect();
      return { cls: String(el.className || el.tagName).slice(0, 90), top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height) };
    });

    const clippedHeaders = headers.filter(h => h.top < -2 || h.bottom > innerHeight + 2);

    const blocks = [...document.querySelectorAll("main section,main article,main aside")].filter(visible).map(el => {
      const r = el.getBoundingClientRect();
      return { name: (el.id || el.className || el.tagName).toString().slice(0, 90), top: Math.round(r.top + scrollY), bottom: Math.round(r.bottom + scrollY), height: Math.round(r.height) };
    }).filter(x => x.height > 30).sort((a,b) => a.top - b.top);

    const largeGaps = [];
    for (let i = 0; i < blocks.length - 1; i++) {
      const gap = blocks[i + 1].top - blocks[i].bottom;
      if (gap > 240) largeGaps.push({ after: blocks[i].name, before: blocks[i + 1].name, gap });
    }

    const primaryCtas = [...document.querySelectorAll(".ff-button--primary,.ff-btn--primary,[data-ff-open-checkout],[data-ff-payment-trigger],[data-ff-home-launch-cta],.ff-onboardButton--primary")].filter(visible).length;

    return {
      title: document.title,
      textSample: text.replace(/\s+/g, " ").trim().slice(0, 650),
      hrefs,
      selectorCounts,
      bad,
      unnamed,
      controlCount: controls.length,
      overflowX,
      clippedHeaders,
      largeGaps,
      primaryCtas
    };
  }, {
    surface,
    badBaseRaw: badBase.map(([n, r]) => [n, r.source, r.flags]),
    badPublicRaw: badPublic.map(([n, r]) => [n, r.source, r.flags])
  });

  if (httpStatus >= 400 || httpStatus === 0) flag(flags, "fail", "http_status", `HTTP ${httpStatus}`);

  for (const css of surface.css) {
    if (!data.hrefs.some(h => h.includes(`/css/${css}`) || h.includes(`css/${css}`))) {
      flag(flags, "fail", "missing_css", `${css} not loaded`);
    }
  }

  for (const [sel, count] of Object.entries(data.selectorCounts)) {
    if (!count) flag(flags, "fail", "missing_selector", sel);
  }

  for (const b of data.bad) {
    flag(flags, "fail", `visible_bad_copy_${b.name}`, `"${b.match}" visible: ${b.context}`);
  }

  if (data.unnamed.length) flag(flags, "fail", "unnamed_controls", `${data.unnamed.length} visible controls have no accessible name`, data.unnamed);
  if (data.overflowX > 4) flag(flags, "fail", "horizontal_overflow", `${data.overflowX}px overflow`);
  if (data.clippedHeaders.length) flag(flags, "fail", "header_clipping", "Header/nav appears clipped", data.clippedHeaders);
  if (consoleErrors.length) flag(flags, "fail", "console_errors", consoleErrors.slice(0, 6).join(" | "));
  if (pageErrors.length) flag(flags, "fail", "page_errors", pageErrors.slice(0, 6).join(" | "));
  if (data.primaryCtas < 1) flag(flags, "warn", "primary_cta_weak", "No obvious visible primary CTA detected");
  if (data.largeGaps.length) flag(flags, "warn", "large_vertical_gaps", "Large rhythm gaps detected", data.largeGaps.slice(0, 8));

  await page.close();

  const status = flags.some(f => f.level === "fail") ? "FAIL" : flags.some(f => f.level === "warn") ? "WARN" : "PASS";
  return { id: surface.id, name: surface.name, viewport, url: fullUrl, httpStatus, status, flags, data };
}

const browser = await chromium.launch({ headless: true });
const desktop = await browser.newContext({ viewport: { width: 1440, height: 1050 }, reducedMotion: "reduce" });
const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: "reduce" });

const results = [];
for (const s of surfaces) {
  results.push(await auditOne(desktop, s, "desktop"));
  results.push(await auditOne(mobile, s, "mobile"));
}

await browser.close();

const flags = results.flatMap(r => r.flags.map(f => ({ surface: r.name, viewport: r.viewport, ...f })));
const fails = flags.filter(f => f.level === "fail");
const warns = flags.filter(f => f.level === "warn");
const status = fails.length ? "FAIL" : warns.length ? "WARN" : "PASS";

const report = { status, base: BASE, run: RUN, counts: { fails: fails.length, warns: warns.length, surfaces: results.length }, results };

fs.writeFileSync(path.join(OUT, "premium-demo-readiness.json"), JSON.stringify(report, null, 2));

let md = `# FutureFunded Premium Demo Readiness Audit\n\nStatus: **${status}**\n\nBase: \`${BASE}\`\nRun: \`${RUN}\`\n\nFailures: **${fails.length}**\nWarnings: **${warns.length}**\n\n## Surface summary\n\n| Surface | Viewport | Status |\n|---|---:|---:|\n`;
for (const r of results) md += `| ${r.name} | ${r.viewport} | ${r.status} |\n`;

md += `\n## Flags\n\n`;
if (!flags.length) {
  md += `No flags found.\n`;
} else {
  md += `| Level | Surface | Viewport | Code | Message |\n|---|---|---:|---|---|\n`;
  for (const f of flags) {
    md += `| ${f.level.toUpperCase()} | ${f.surface} | ${f.viewport} | \`${f.code}\` | ${String(f.msg).replace(/\|/g, "\\|")} |\n`;
  }
}

fs.writeFileSync(path.join(OUT, "premium-demo-readiness.md"), md);

fs.rmSync(LATEST, { recursive: true, force: true });
fs.cpSync(OUT, LATEST, { recursive: true });

console.log(`\nPREMIUM DEMO READINESS: ${status}`);
console.log(`Failures: ${fails.length}`);
console.log(`Warnings: ${warns.length}`);
console.log(`Output: ${OUT}`);
console.log(`Latest: ${LATEST}`);

for (const f of flags.slice(0, 20)) {
  console.log(`- [${f.level.toUpperCase()}] ${f.surface} / ${f.viewport} / ${f.code}: ${String(f.msg).slice(0, 220)}`);
}

process.exit(fails.length ? 1 : 0);

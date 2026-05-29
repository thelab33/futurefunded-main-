#!/usr/bin/env node
import fs from "node:fs/promises";
import fss from "node:fs";
import path from "node:path";

let playwright;
try {
  playwright = await import("@playwright/test");
} catch {
  playwright = await import("playwright");
}

const { chromium } = playwright;

const ROOT = process.cwd();
const BASE_URL = (process.env.FF_BASE_URL || "https://getfuturefunded.com").replace(/\/+$/, "");
const OUT_ROOT = path.join(ROOT, "audit_outputs", "hoi-6d-cta-semantics");
const STAMP = new Date().toISOString().replace(/[:.]/g, "-");
const RUN_DIR = path.join(OUT_ROOT, STAMP);
const LATEST_DIR = path.join(OUT_ROOT, "latest");

const PAGES = [
  { key: "platform", label: "Platform homepage", path: "/platform/" },
  { key: "campaign", label: "Campaign page", path: "/c/connect-atx-elite" },
  { key: "login", label: "Login", path: "/platform/login" },
  { key: "onboarding", label: "Onboarding", path: "/platform/onboarding" },
  { key: "dashboard_locked", label: "Dashboard locked", path: "/platform/dashboard", protected: true },
];

const VIEWPORTS = [
  { key: "mobile", width: 390, height: 844 },
  { key: "desktop", width: 1440, height: 1100 },
];

function clean(value = "") {
  return String(value).replace(/\s+/g, " ").trim();
}

function wordCount(value = "") {
  return clean(value).split(/\s+/).filter(Boolean).length;
}

function urlFor(pagePath) {
  return new URL(pagePath, `${BASE_URL}/`).toString();
}

function isLikelyBrandOrHome(text = "") {
  return /FutureFunded.*home|campaign home|platform home|ORGANIZER ACCESS|LAUNCH WORKSPACE|PROTECTED DASHBOARD|FUNDRAISING PLATFORM/i.test(text);
}

function isLikelyAmountCard(text = "") {
  return /^\$\d+/.test(clean(text)) && /donate\s+\$\d+/i.test(text);
}

function recommendedLabel(text = "") {
  const t = clean(text);

  const amount = t.match(/\$(\d[\d,]*)/);
  if (amount && /donate/i.test(t)) return `Donate $${amount[1]}`;

  if (/sponsor/i.test(t)) return "Become a sponsor";
  if (/share/i.test(t)) return "Share campaign";
  if (/copy/i.test(t)) return "Copy link";
  if (/login|sign in/i.test(t)) return "Sign in";
  if (/campaign preview|open live/i.test(t)) return "View campaign";
  if (/home/i.test(t)) return "FutureFunded home";

  return t.split(/\s+/).slice(0, 4).join(" ");
}

async function ensureDirs() {
  await fs.mkdir(RUN_DIR, { recursive: true });
}

async function copyLatest() {
  await fs.rm(LATEST_DIR, { recursive: true, force: true });
  await fs.cp(RUN_DIR, LATEST_DIR, { recursive: true });
}

async function auditPage(browser, pageDef, viewport) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });

  const page = await context.newPage();
  const url = urlFor(pageDef.path);
  let status = null;

  try {
    const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
    status = response?.status() ?? null;
    await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
    await page.evaluate(() => document.fonts?.ready).catch(() => {});
    await page.waitForTimeout(250);
  } catch {}

  const controls = await page.evaluate(() => {
    const visible = (el) => {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };

    const cssPath = (el) => {
      if (!el || !el.tagName) return "";
      const parts = [];
      let node = el;
      while (node && node.nodeType === 1 && parts.length < 5) {
        let part = node.tagName.toLowerCase();
        const ffAttrs = [...node.attributes]
          .filter((a) => a.name.startsWith("data-ff"))
          .map((a) => `[${a.name}${a.value ? `="${a.value}"` : ""}]`)
          .join("");
        if (ffAttrs) part += ffAttrs;
        else if (node.id) part += `#${node.id}`;
        else if (node.className && typeof node.className === "string") {
          const cls = node.className.trim().split(/\s+/).slice(0, 2).join(".");
          if (cls) part += `.${cls}`;
        }
        parts.unshift(part);
        node = node.parentElement;
      }
      return parts.join(" > ");
    };

    return [
      ...document.querySelectorAll("a,button,[role='button'],input[type='submit'],input[type='button']")
    ]
      .filter(visible)
      .map((el) => {
        const text = [
          el.innerText,
          el.getAttribute("value"),
        ].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();

        const aria = el.getAttribute("aria-label") || "";
        const title = el.getAttribute("title") || "";
        const hooks = [...el.attributes]
          .filter((a) => a.name.startsWith("data-ff"))
          .map((a) => `${a.name}${a.value ? `=${a.value}` : ""}`);

        return {
          tag: el.tagName.toLowerCase(),
          text,
          aria,
          title,
          href: el.getAttribute("href") || "",
          hooks,
          selector: cssPath(el),
          className: typeof el.className === "string" ? el.className.slice(0, 220) : "",
        };
      });
  });

  await context.close();

  const findings = controls
    .map((control) => {
      const visibleText = clean(control.text);
      const accessibleName = clean(control.aria || control.title || control.text);
      const words = wordCount(accessibleName);
      const ignored =
        isLikelyBrandOrHome(accessibleName) ||
        isLikelyBrandOrHome(visibleText);

      const amountCard = isLikelyAmountCard(visibleText) || isLikelyAmountCard(accessibleName);

      const needsShortAria =
        !ignored &&
        (amountCard || words > 5) &&
        !/^Donate \$\d[\d,]*$/i.test(accessibleName) &&
        !/^Become a sponsor$/i.test(accessibleName) &&
        !/^Share campaign$/i.test(accessibleName) &&
        !/^Copy link$/i.test(accessibleName);

      return {
        ...control,
        ignored,
        amountCard,
        wordCount: words,
        needsShortAria,
        recommendedAria: needsShortAria ? recommendedLabel(accessibleName || visibleText) : "",
      };
    })
    .filter((control) => control.needsShortAria);

  return {
    page: pageDef.key,
    label: pageDef.label,
    viewport: viewport.key,
    url,
    status,
    totalControls: controls.length,
    findings,
  };
}

function buildMarkdown(report) {
  const lines = [
    "# FutureFunded HOI 6D — CTA Semantic Names Audit",
    "",
    `**Status:** ${report.ok ? "PASS ✅" : "REVIEW ⚠️"}`,
    `**Base URL:** ${report.baseUrl}`,
    `**Checked:** ${report.checkedAt}`,
    "",
    "## Purpose",
    "",
    "This checks whether visually rich cards and CTAs have concise accessible names. A donation card can visually say more, but the control name should stay short, such as `Donate $25`.",
    "",
    "## Summary",
    "",
    `- Total findings: ${report.totalFindings}`,
    "",
  ];

  for (const result of report.results) {
    lines.push(`## ${result.label} / ${result.viewport}`);
    lines.push("");
    lines.push(`- URL: ${result.url}`);
    lines.push(`- Status: ${result.status}`);
    lines.push(`- Controls: ${result.totalControls}`);
    lines.push(`- Findings: ${result.findings.length}`);
    lines.push("");

    if (!result.findings.length) {
      lines.push("- ✅ No semantic CTA issues found.");
      lines.push("");
      continue;
    }

    for (const f of result.findings.slice(0, 20)) {
      lines.push(`- **Current:** “${f.text.slice(0, 220)}${f.text.length > 220 ? "…" : ""}”`);
      lines.push(`  - Recommended aria-label: \`${f.recommendedAria}\``);
      lines.push(`  - Selector: \`${f.selector}\``);
      if (f.hooks.length) lines.push(`  - Hooks: \`${f.hooks.join(", ")}\``);
      lines.push("");
    }
  }

  lines.push(
    "## Patch guidance",
    "",
    "- Keep visual card copy rich.",
    "- Add concise `aria-label` values to card-like links/buttons.",
    "- Donation cards should read like `Donate $25`, `Donate $50`, etc.",
    "- Sponsor/share CTAs should read like `Become a sponsor` and `Share campaign`.",
    "- Do not remove or rename `data-ff-*` hooks.",
    ""
  );

  return lines.join("\n");
}

await ensureDirs();

const browser = await chromium.launch({ headless: true });
const results = [];

for (const pageDef of PAGES) {
  for (const viewport of VIEWPORTS) {
    console.log(`Auditing CTA semantics: ${pageDef.label} / ${viewport.key}`);
    results.push(await auditPage(browser, pageDef, viewport));
  }
}

await browser.close();

const totalFindings = results.reduce((sum, result) => sum + result.findings.length, 0);
const report = {
  ok: totalFindings === 0,
  checkedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  totalFindings,
  results,
};

await fs.writeFile(path.join(RUN_DIR, "report.json"), JSON.stringify(report, null, 2) + "\n");
await fs.writeFile(path.join(RUN_DIR, "report.md"), buildMarkdown(report));

await copyLatest();

console.log("");
console.log(fss.readFileSync(path.join(LATEST_DIR, "report.md"), "utf8"));
console.log("");
console.log(`CTA semantic report: ${path.join(LATEST_DIR, "report.md")}`);

process.exit(report.ok ? 0 : 1);

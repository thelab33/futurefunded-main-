#!/usr/bin/env node
/**
 * FutureFunded • Wave 6C Founder Demo Package
 *
 * Creates a clean founder-demo package:
 * - final screenshots
 * - route proof
 * - demo links
 * - stakeholder checklist
 * - no secrets printed
 */

import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const ROOT = process.cwd();
const STAMP = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "");
const OUT_DIR = path.join(ROOT, "audit_outputs", "founder-demo-package");
fs.mkdirSync(OUT_DIR, { recursive: true });

const routes = [
  {
    name: "Platform Homepage",
    slug: "platform",
    url: "http://127.0.0.1:5000/platform",
    live: "https://getfuturefunded.com/platform/"
  },
  {
    name: "Campaign Demo",
    slug: "campaign",
    url: "http://127.0.0.1:5000/c/connect-atx-elite",
    live: "https://getfuturefunded.com/c/connect-atx-elite"
  },
  {
    name: "Onboarding Workspace",
    slug: "onboarding",
    url: "http://127.0.0.1:5000/platform/onboarding",
    live: "https://getfuturefunded.com/platform/onboarding"
  },
  {
    name: "Protected Operator Dashboard",
    slug: "dashboard",
    url: "http://127.0.0.1:5000/platform/dashboard",
    live: "https://getfuturefunded.com/platform/dashboard"
  }
];

const viewports = [
  { name: "mobile", width: 390, height: 844, scale: 2 },
  { name: "desktop", width: 1440, height: 1100, scale: 1 }
];

function rel(file) {
  return path.relative(ROOT, file);
}

async function pageProof(page) {
  return page.evaluate(() => {
    const bodyText = document.body.innerText.replace(/\s+/g, " ").trim();
    const headings = [...document.querySelectorAll("h1,h2,h3")]
      .filter((el) => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
      })
      .map((el) => `${el.tagName.toLowerCase()}: ${el.innerText.trim().replace(/\s+/g, " ")}`)
      .slice(0, 10);

    const ctas = [...document.querySelectorAll("a,button")]
      .filter((el) => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
      })
      .map((el) => (el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " "))
      .filter(Boolean)
      .slice(0, 18);

    return {
      title: document.title,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      hasDonate: /donate|give securely|back the season/i.test(bodyText),
      hasSponsor: /sponsor|package|partner|business/i.test(bodyText),
      hasTrust: /secure|receipt|confirmation|verified|email|operator/i.test(bodyText),
      headings,
      ctas
    };
  });
}

const browser = await chromium.launch({ headless: true, args: ["--disable-dev-shm-usage", "--no-sandbox"] });
const results = [];

for (const vp of viewports) {
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: vp.scale,
    isMobile: vp.name === "mobile",
    hasTouch: vp.name === "mobile"
  });

  const page = await context.newPage();

  for (const route of routes) {
    const file = path.join(OUT_DIR, `${STAMP}-${route.slug}-${vp.name}.png`);
    let status = null;
    let proof = null;
    let error = "";

    try {
      const res = await page.goto(route.url, { waitUntil: "domcontentloaded", timeout: 18000 });
      status = res?.status() ?? null;
      await page.waitForTimeout(1000);
      await page.screenshot({ path: file, fullPage: true });
      proof = await pageProof(page);
    } catch (err) {
      error = `${err.name || "Error"}: ${err.message}`;
    }

    results.push({
      route: route.name,
      slug: route.slug,
      viewport: vp.name,
      localUrl: route.url,
      liveUrl: route.live,
      status,
      ok: [200, 403].includes(status),
      screenshot: rel(file),
      error,
      proof
    });
  }

  await context.close();
}

await browser.close();

const jsonPath = path.join(OUT_DIR, `ff_wave6c_founder_demo_package_${STAMP}.json`);
const mdPath = path.join(OUT_DIR, `ff_wave6c_founder_demo_package_${STAMP}.md`);

fs.writeFileSync(jsonPath, JSON.stringify({ generatedAt: new Date().toISOString(), results }, null, 2));

const lines = [];

lines.push("# FutureFunded Wave 6C Founder Demo Package");
lines.push("");
lines.push(`- **Generated:** \`${new Date().toISOString()}\``);
lines.push(`- **Screenshots:** \`${rel(OUT_DIR)}\``);
lines.push("");

lines.push("## Demo links");
lines.push("");
lines.push("| Surface | Live URL | Purpose |");
lines.push("| --- | --- | --- |");
lines.push("| Platform Homepage | https://getfuturefunded.com/platform/ | Sell the product vision |");
lines.push("| Campaign Demo | https://getfuturefunded.com/c/connect-atx-elite | Show donor/sponsor conversion |");
lines.push("| Onboarding Workspace | https://getfuturefunded.com/platform/onboarding | Show launch workflow |");
lines.push("| Operator Dashboard | https://getfuturefunded.com/platform/dashboard | Show protected operator console |");
lines.push("");

lines.push("## Screenshot proof");
lines.push("");
lines.push("| Surface | Viewport | HTTP | Overflow | Donate | Sponsor | Trust | Screenshot |");
lines.push("| --- | --- | ---: | --- | --- | --- | --- | --- |");

for (const r of results) {
  const p = r.proof;
  lines.push(
    `| ${r.route} | ${r.viewport} | ${r.status ?? "ERR"} ${r.ok ? "✅" : "❌"} | ` +
    `${p?.overflow ? "❌" : "✅"} | ` +
    `${p?.hasDonate ? "✅" : "—"} | ` +
    `${p?.hasSponsor ? "✅" : "—"} | ` +
    `${p?.hasTrust ? "✅" : "—"} | ` +
    `\`${r.screenshot}\` |`
  );
}

lines.push("");
lines.push("## Talk track");
lines.push("");
lines.push("1. **Platform:** FutureFunded sells premium fundraising pages for teams, schools, nonprofits, and clubs.");
lines.push("2. **Campaign:** The donor sees a clear story, secure giving, sponsor packages, and share actions.");
lines.push("3. **Money loop:** Stripe test donations and sponsor payments have been verified through paid completion.");
lines.push("4. **Follow-up loop:** Postmark SMTP sends donor receipts, sponsor confirmations, and operator alerts.");
lines.push("5. **Onboarding:** The setup page works as a launch room for campaign identity, sponsor packages, payment readiness, and media.");
lines.push("6. **Dashboard:** The operator console is intentionally protected and ready for private organizer access.");
lines.push("");

lines.push("## Demo-safe reminders");
lines.push("");
lines.push("- Do not show raw `.env` files.");
lines.push("- Do not show `pm2 jlist` raw output.");
lines.push("- Do not show Stripe secret keys, Postmark tokens, Cloudflare API tokens, or tunnel credentials.");
lines.push("- Use screenshots and docs for stakeholders; use CLI only for private proof.");
lines.push("");

fs.writeFileSync(mdPath, lines.join("\n"));

console.log(`✅ Wave 6C founder demo package: ${mdPath}`);
console.log(`JSON: ${jsonPath}`);

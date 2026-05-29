import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "https://getfuturefunded.com";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || process.env.OPERATOR_TOKEN || "";

const checks = [];

function record(ok, label, detail = "") {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? ` — ${detail}` : ""}`);
}

const browser = await chromium.launch({ headless: true });

async function auditPage(path, label, opts = {}) {
  for (const viewport of [
    { name: "desktop", width: 1440, height: 1050 },
    { name: "mobile", width: 390, height: 900 },
  ]) {
    const page = await browser.newPage({ viewport });
    const response = await page.goto(`${base}${path}${path.includes("?") ? "&" : "?"}dashboard_final_audit=${Date.now()}`, {
      waitUntil: "networkidle",
    });

    const status = response?.status() || 0;
    const okStatus = opts.allowForbidden ? status >= 200 && status < 500 : status >= 200 && status < 400;
    record(okStatus, `${label} responds [${viewport.name}]`, `status=${status}`);

    const cssLinked = await page.locator('link[href*="dashboard-modern.css"], link[href*="login.css"]').count().catch(() => 0);
    record(cssLinked > 0, `${label} loads a protected access stylesheet [${viewport.name}]`, `count=${cssLinked}`);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1).catch(() => false);
    record(!overflow, `${label} has no horizontal overflow [${viewport.name}]`, `overflow=${overflow}`);

    const text = await page.locator("body").innerText().catch(() => "");
    record(!/{{|{%|%}/.test(text), `${label} has no visible template leak [${viewport.name}]`);

    for (const marker of opts.markers || []) {
      record(text.toLowerCase().includes(marker.toLowerCase()), `${label} copy marker remains: ${marker} [${viewport.name}]`);
    }

    if (opts.locked) {
      const queueVisible = await page.locator('[data-ff-sponsor-review-queue]').count().catch(() => 0);
      record(queueVisible === 0, `${label} does not expose sponsor review queue [${viewport.name}]`, `count=${queueVisible}`);
    }

    if (opts.modern) {
      const bodyClass = await page.locator("body").getAttribute("class").catch(() => "");
      record((bodyClass || "").includes("ff-dashboardModernBody"), `${label} modern body scope present [${viewport.name}]`);

      const heroBox = await page.locator(".ff-dashboardModern__hero").boundingBox().catch(() => null);
      record((heroBox?.height || 0) > 0 && (heroBox?.height || 9999) < (viewport.name === "desktop" ? 520 : 720), `${label} hero height controlled [${viewport.name}]`, `height=${Math.round(heroBox?.height || 0)}`);
    }

    await page.close();
  }
}

await auditPage("/platform/dashboard", "Locked dashboard handoff", {
  allowForbidden: true,
  locked: true,
  markers: ["Operator access required", "Protected workspace"],
});

if (token) {
  await auditPage(`/platform/dashboard?operator_token=${encodeURIComponent(token)}`, "Protected dashboard", {
    modern: true,
    markers: ["Campaign command center", "Next actions", "Readiness", "Operations & records"],
  });
} else {
  console.log("SKIP Protected dashboard token audit — FF_OPERATOR_ACCESS_TOKEN not set.");
}

await browser.close();

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;

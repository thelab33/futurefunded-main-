import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "https://getfuturefunded.com";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || "";

if (!token) {
  console.error("Missing FF_OPERATOR_ACCESS_TOKEN");
  process.exit(1);
}

const url = `${base}/platform/dashboard?operator_token=${encodeURIComponent(token)}&paint_trace=${Date.now()}`;
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });

const snapshots = [];

async function snap(label) {
  const data = await page.evaluate((label) => {
    const html = document.documentElement;
    const assistant =
      document.querySelector("[data-ff-dashboard-launch-assistant]") ||
      document.querySelector("[data-ff-launch-assistant]") ||
      document.querySelector(".ff-launchAssistant") ||
      document.querySelector(".ff-dashboardExecutiveAssistant");

    const dashboard = document.querySelector("main.ff-dashboardModern, .ff-dashboardModern");
    const hero = document.querySelector(".ff-dashboardModern__hero");

    const rect = (node) => {
      if (!node) return null;
      const r = node.getBoundingClientRect();
      return {
        top: Math.round(r.top),
        left: Math.round(r.left),
        width: Math.round(r.width),
        height: Math.round(r.height),
        display: getComputedStyle(node).display,
        visibility: getComputedStyle(node).visibility,
        opacity: getComputedStyle(node).opacity,
      };
    };

    return {
      label,
      classes: html.className,
      ready: html.classList.contains("ff-dashboard-protected-exec-ready"),
      hardboot: html.classList.contains("ff-dashboard-hardboot"),
      booting: html.classList.contains("ff-dashboard-protected-booting"),
      hasRuntime: Boolean(window.FutureFundedDashboardProtectedExec),
      dashboard: rect(dashboard),
      hero: rect(hero),
      assistant: rect(assistant),
      textStart: document.body?.innerText?.slice(0, 180).replace(/\s+/g, " ") || "",
    };
  }, label);

  snapshots.push(data);
}

page.on("domcontentloaded", async () => {
  await snap("domcontentloaded");
});

await page.goto(url, { waitUntil: "commit" });
await snap("commit");

await page.waitForTimeout(50);
await snap("50ms");

await page.waitForTimeout(150);
await snap("200ms");

await page.waitForLoadState("networkidle").catch(() => {});
await snap("networkidle");

await page.waitForTimeout(500);
await snap("networkidle+500ms");

console.log(JSON.stringify({ url, snapshots }, null, 2));

await browser.close();

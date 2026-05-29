import { chromium } from "playwright";
import fs from "node:fs/promises";

const url = process.env.FF_CAMPAIGN_URL || "http://127.0.0.1:5000/c/connect-atx-elite";
const out = "artifacts/frontend-screenshots/share-qr-dom-probe.json";

await fs.mkdir("artifacts/frontend-screenshots", { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 1200 } });

await page.goto(url, { waitUntil: "networkidle" });

const before = await page.evaluate(() => ({
  runtime: window.FutureFundedShareQr?.version || null,
  triggerCount: document.querySelectorAll("[data-ff-qr-trigger], [data-ff-share-trigger], [data-ff-share='true']").length,
  drawers: Array.from(document.querySelectorAll("#qr-modal, [data-ff-share-drawer], [data-ff-qr-modal], .ff-shareDrawer")).map((node) => {
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();

    return {
      id: node.id || "",
      hidden: node.hidden,
      ariaHidden: node.getAttribute("aria-hidden"),
      display: style.display,
      visibility: style.visibility,
      opacity: style.opacity,
      pointerEvents: style.pointerEvents,
      width: rect.width,
      height: rect.height,
      shareOpen: node.getAttribute("data-ff-share-open"),
    };
  }),
}));

await page.locator("[data-ff-qr-trigger], [data-ff-share-trigger], [data-ff-share='true']").first().click();
await page.waitForTimeout(650);

const after = await page.evaluate(() => ({
  runtime: window.FutureFundedShareQr?.version || null,
  drawers: Array.from(document.querySelectorAll("#qr-modal, [data-ff-share-drawer], [data-ff-qr-modal], .ff-shareDrawer")).map((node) => {
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();

    return {
      id: node.id || "",
      hidden: node.hidden,
      ariaHidden: node.getAttribute("aria-hidden"),
      display: style.display,
      visibility: style.visibility,
      opacity: style.opacity,
      pointerEvents: style.pointerEvents,
      width: rect.width,
      height: rect.height,
      shareOpen: node.getAttribute("data-ff-share-open"),
      visible:
        !node.hidden &&
        node.getAttribute("aria-hidden") !== "true" &&
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        Number(style.opacity || "1") > 0 &&
        rect.width > 20 &&
        rect.height > 20,
    };
  }),
  copyHooks: document.querySelectorAll(
    "[data-ff-copy-share-url], [data-ff-copy-trigger], [data-ff-copy-link], #qr-modal-share-url, [data-ff-qr-share-url]"
  ).length,
}));

const payload = {
  url,
  ok: Boolean(after.runtime) && after.drawers.some((drawer) => drawer.visible) && after.copyHooks > 0,
  checkedAt: new Date().toISOString(),
  before,
  after,
};

await fs.writeFile(out, `${JSON.stringify(payload, null, 2)}\n`);
console.log(JSON.stringify(payload, null, 2));

await browser.close();

if (!payload.ok) process.exit(1);

import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const url =
  process.env.CAMPAIGN_URL ||
  process.env.FF_CAMPAIGN_URL ||
  "http://127.0.0.1:5000/c/connect-atx-elite";

const historyDir = process.env.FF_SCREENSHOT_DIR || "artifacts/screenshots";
const latestDir = process.env.FF_SCREENSHOT_LATEST_DIR || "artifacts/frontend-screenshots";
const stamp = new Date().toISOString().replace(/[:.]/g, "-");

const shots = [
  {
    name: "campaign-desktop",
    historyName: `campaign-desktop-${stamp}.png`,
    latestName: "campaign-desktop.png",
    viewport: { width: 1440, height: 2400 },
    fullPage: true,
  },
  {
    name: "campaign-mobile",
    historyName: `campaign-mobile-${stamp}.png`,
    latestName: "campaign-mobile.png",
    viewport: { width: 390, height: 2200 },
    fullPage: true,
  },
];

async function warmLazyContent(page) {
  await page.evaluate(async () => {
    const step = Math.max(320, Math.floor(window.innerHeight * 0.72));
    const maxY = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);

    for (let y = 0; y <= maxY; y += step) {
      window.scrollTo(0, y);
      await new Promise((resolve) => setTimeout(resolve, 80));
    }

    window.scrollTo(0, maxY);
    await new Promise((resolve) => setTimeout(resolve, 180));
    window.scrollTo(0, 0);
  });

  await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});

  await page
    .waitForFunction(
      () =>
        Array.from(document.querySelectorAll("[data-ff-team-media-image]")).every(
          (img) => img.complete
        ),
      null,
      { timeout: 8_000 }
    )
    .catch(() => {});
}

await fs.mkdir(historyDir, { recursive: true });
await fs.mkdir(latestDir, { recursive: true });

const browser = await chromium.launch({ headless: true });

try {
  for (const shot of shots) {
    const context = await browser.newContext({
      viewport: shot.viewport,
      deviceScaleFactor: 1,
      bypassCSP: true,
    });

    const page = await context.newPage();
    page.setDefaultTimeout(35_000);

    const response = await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 45_000,
    });

    if (!response || !response.ok()) {
      throw new Error(
        `Could not load campaign URL: ${url}. Status: ${response?.status() ?? "no response"}`
      );
    }

    await page.waitForSelector("#campaign-main");
    await page.waitForSelector("#campaign-hero");
    await page.waitForSelector('[data-ff-section="sponsors"]');

    await page.emulateMedia({
      reducedMotion: "reduce",
    });

    await page.addStyleTag({
      content: `
        *, *::before, *::after {
          animation-duration: 0.001ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.001ms !important;
          scroll-behavior: auto !important;
        }

        .ff-mobile-rail {
          transform: none !important;
        }
      `,
    });

    await warmLazyContent(page);

    await page.evaluate(() => {
      window.scrollTo(0, 0);
    });

    const historyPath = path.join(historyDir, shot.historyName);
    const latestPath = path.join(latestDir, shot.latestName);

    await page.screenshot({
      path: historyPath,
      fullPage: shot.fullPage,
    });

    await fs.copyFile(historyPath, latestPath);

    await context.close();

    console.log(`✅ Saved history: ${historyPath}`);
    console.log(`✅ Updated latest: ${latestPath}`);
  }
} finally {
  await browser.close();
}

console.log("");
console.log("Open or attach artifacts/frontend-screenshots/campaign-desktop.png for review.");

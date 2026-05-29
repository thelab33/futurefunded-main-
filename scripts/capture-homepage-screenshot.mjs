import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const url =
  process.env.HOMEPAGE_URL || process.env.PLATFORM_URL || "http://127.0.0.1:5000/platform/";

const historyDir = "artifacts/screenshots";
const latestDir = "artifacts/frontend-screenshots";
const stamp = new Date().toISOString().replace(/[:.]/g, "-");

const shots = [
  {
    historyName: `homepage-desktop-${stamp}.png`,
    latestName: "homepage-desktop.png",
    viewport: { width: 1440, height: 2600 },
  },
  {
    historyName: `homepage-mobile-${stamp}.png`,
    latestName: "homepage-mobile.png",
    viewport: { width: 390, height: 2400 },
  },
];

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
    page.setDefaultTimeout(25_000);

    const response = await page.goto(url, {
      waitUntil: "networkidle",
      timeout: 45_000,
    });

    if (!response || !response.ok()) {
      throw new Error(
        `Could not load homepage URL: ${url}. Status: ${response?.status() ?? "no response"}`
      );
    }

    await page.waitForSelector("[data-ff-home-root]");
    await page.waitForSelector("#home-main");

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
      `,
    });

    await page.evaluate(() => {
      window.scrollTo(0, 0);
    });

    const historyPath = path.join(historyDir, shot.historyName);
    const latestPath = path.join(latestDir, shot.latestName);

    await page.screenshot({
      path: historyPath,
      fullPage: true,
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
console.log("Open artifacts/frontend-screenshots/homepage-desktop.png for review.");

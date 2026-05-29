import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const BASE_URL = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const OUT_DIR = process.env.FF_SCREENSHOT_DIR || "artifacts/frontend-screenshots";
const TOKEN_FILE = "/tmp/ff_operator_token";

async function readToken() {
  const fromEnv = (process.env.FF_OPERATOR_ACCESS_TOKEN || "").trim();
  if (fromEnv) return fromEnv;

  try {
    const fromFile = (await fs.readFile(TOKEN_FILE, "utf8")).trim();
    if (fromFile) {
      process.env.FF_OPERATOR_ACCESS_TOKEN = fromFile;
      return fromFile;
    }
  } catch {
    return "";
  }

  return "";
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

const token = await readToken();

const productPages = [
  {
    name: "homepage",
    label: "Homepage",
    path: "/platform/",
    waitFor: ".ff-home, [data-ff-home-root]",
  },
  {
    name: "campaign",
    label: "Campaign",
    path: "/c/connect-atx-elite",
    waitFor: "[data-ff-page-root], .page-campaign, .campaign-page",
  },
  {
    name: "login",
    label: "Login",
    path: "/platform/login",
    waitFor: "[data-ff-login-root]",
  },
  {
    name: "dashboard",
    label: "Dashboard",
    path: token
      ? `/platform/dashboard?operator_token=${encodeURIComponent(token)}`
      : "/platform/dashboard",
    waitFor: "[data-ff-operator-root]",
  },
];

if (process.env.INCLUDE_ONBOARDING === "1") {
  productPages.push({
    name: "onboarding",
    label: "Onboarding",
    path: "/platform/onboarding",
    waitFor: "body",
  });
}

const viewports = [
  {
    name: "desktop",
    width: 1440,
    height: 1100,
    deviceScaleFactor: 1,
    isMobile: false,
  },
  {
    name: "mobile",
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    isMobile: true,
  },
];

await fs.mkdir(OUT_DIR, { recursive: true });

const browser = await chromium.launch({
  headless: true,
});

const manifest = {
  baseUrl: BASE_URL,
  createdAt: new Date().toISOString(),
  outputDir: OUT_DIR,
  tokenSource: token ? TOKEN_FILE : null,
  pages: [],
};

const failures = [];

for (const viewport of viewports) {
  const context = await browser.newContext({
    viewport: {
      width: viewport.width,
      height: viewport.height,
    },
    deviceScaleFactor: viewport.deviceScaleFactor,
    isMobile: viewport.isMobile,
    hasTouch: viewport.isMobile,
    colorScheme: "light",
    reducedMotion: "reduce",
  });

  for (const spec of productPages) {
    const page = await context.newPage();

    const url = `${BASE_URL}${spec.path}`;
    const redactedUrl = token ? url.replaceAll(token, "<redacted>") : url;
    const safeName = `${spec.name}-${viewport.name}`;
    const fullPath = path.join(OUT_DIR, `${safeName}.png`);

    console.log(`Capturing ${safeName}: ${redactedUrl}`);

    let status = null;
    let title = "";

    try {
      const response = await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 30000,
      });

      status = response ? response.status() : null;

      try {
        await page.waitForLoadState("networkidle", { timeout: 8000 });
      } catch {
        // Some pages may keep lightweight polling or dev tooling requests alive.
      }

      try {
        await page.waitForSelector(spec.waitFor, {
          timeout: 12000,
        });
      } catch {
        if (spec.name === "dashboard") {
          console.warn(`WARN: ${safeName}: selector not found: ${spec.waitFor}`);
        } else {
          failures.push(`${safeName}: selector not found: ${spec.waitFor}`);
        }
      }

      await page.evaluate(() => {
        document.documentElement.style.scrollBehavior = "auto";
        document.body.style.scrollBehavior = "auto";
        window.scrollTo(0, 0);
      });

      await page.screenshot({
        path: fullPath,
        fullPage: true,
        animations: "disabled",
        caret: "hide",
      });

      title = await page.title();

      if (status && status >= 400) {
        if (spec.name === "dashboard" && status === 403) {
          console.warn(
            `WARN: ${safeName}: dashboard returned 403; check /tmp/ff_operator_token or restart Flask with FF_OPERATOR_ACCESS_TOKEN`
          );
        } else {
          failures.push(`${safeName}: HTTP ${status}`);
        }
      }

      if (!(await fileExists(fullPath))) {
        failures.push(`${safeName}: screenshot was not written`);
      }
    } catch (error) {
      failures.push(`${safeName}: ${error.message}`);
    }

    manifest.pages.push({
      name: spec.name,
      label: spec.label,
      viewport: viewport.name,
      status,
      title,
      url: redactedUrl,
      file: fullPath,
      width: viewport.width,
      height: viewport.height,
    });

    await page.close();
  }

  await context.close();
}

await browser.close();

await fs.writeFile(path.join(OUT_DIR, "manifest.json"), JSON.stringify(manifest, null, 2));

console.log("");
console.log(`Done. Screenshots saved to: ${OUT_DIR}`);
console.log(`Manifest: ${path.join(OUT_DIR, "manifest.json")}`);

if (failures.length) {
  console.log("");
  console.log("Failures:");
  for (const failure of failures) {
    console.log(`- ${failure}`);
  }
  process.exit(1);
}

import { chromium } from "playwright";

const BASE = process.env.FF_BASE_URL || "http://127.0.0.1:5000";

const ROUTES = [
  ["platform", "/platform/"],
  ["campaign", "/c/connect-atx-elite"],
  ["login", "/platform/login"],
  ["onboarding", "/platform/onboarding"],
  ["dashboard-locked", "/platform/dashboard"],
  ["dashboard-token", `/platform/dashboard${process.env.FF_OPERATOR_ACCESS_TOKEN ? `?access_token=${process.env.FF_OPERATOR_ACCESS_TOKEN}` : ""}`],
];

const viewports = [
  ["mobile", { width: 390, height: 844 }],
  ["desktop", { width: 1440, height: 1100 }],
];

const browser = await chromium.launch({ headless: true });
let failures = 0;

for (const [surface, path] of ROUTES) {
  for (const [viewportName, viewport] of viewports) {
    const page = await browser.newPage({ viewport });
    const url = new URL(path, BASE).toString();

    const consoleErrors = [];
    const pageErrors = [];
    const failedRequests = [];

    page.on("console", msg => {
      if (["error", "warning"].includes(msg.type())) {
        consoleErrors.push(`${msg.type()}: ${msg.text()}`.slice(0, 260));
      }
    });

    page.on("pageerror", err => {
      pageErrors.push(String(err.message || err).slice(0, 260));
    });

    page.on("requestfailed", req => {
      const failure = req.failure();
      failedRequests.push(`${req.url()} :: ${failure?.errorText || "failed"}`.slice(0, 260));
    });

    let status = "ERR";
    try {
      const res = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 35000 });
      status = res ? String(res.status()) : "NO_RESPONSE";
      await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(1200);
    } catch (err) {
      console.log(`\n❌ ${surface}/${viewportName} navigation failed: ${err.message}`);
      failures++;
      await page.close();
      continue;
    }

    const report = await page.evaluate(() => {
      const html = document.documentElement;
      const body = document.body;

      const css = [...document.querySelectorAll('link[rel="stylesheet"]')].map(el => el.getAttribute("href"));
      const js = [...document.querySelectorAll("script[src]")].map(el => el.getAttribute("src"));

      const revealNodes = [...document.querySelectorAll(
        "[data-ff-reveal], [data-ff-animate], .ff-reveal, .ff-revealItem"
      )];

      const hiddenReveal = revealNodes
        .map((el, index) => {
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return {
            index,
            tag: el.tagName.toLowerCase(),
            cls: String(el.className || "").slice(0, 120),
            opacity: cs.opacity,
            visibility: cs.visibility,
            display: cs.display,
            transform: cs.transform,
            hidden: el.hidden,
            ariaHidden: el.getAttribute("aria-hidden"),
            rect: {
              x: Math.round(r.x),
              y: Math.round(r.y),
              w: Math.round(r.width),
              h: Math.round(r.height),
            },
          };
        })
        .filter(item => {
          const op = Number(item.opacity);
          return (
            item.hidden ||
            item.ariaHidden === "true" ||
            item.display === "none" ||
            item.visibility === "hidden" ||
            (!Number.isNaN(op) && op < 0.1)
          );
        })
        .slice(0, 20);

      const blockers = [...document.body.querySelectorAll("*")]
        .map(el => {
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          const z = Number.parseInt(cs.zIndex, 10);
          return {
            tag: el.tagName.toLowerCase(),
            cls: String(el.className || "").slice(0, 120),
            id: el.id || "",
            position: cs.position,
            display: cs.display,
            visibility: cs.visibility,
            opacity: cs.opacity,
            zIndex: cs.zIndex,
            hidden: el.hidden,
            ariaHidden: el.getAttribute("aria-hidden"),
            rect: {
              x: Math.round(r.x),
              y: Math.round(r.y),
              w: Math.round(r.width),
              h: Math.round(r.height),
            },
            score:
              ["fixed", "sticky"].includes(cs.position) &&
              cs.display !== "none" &&
              cs.visibility !== "hidden" &&
              !el.hidden &&
              el.getAttribute("aria-hidden") !== "true" &&
              r.width > window.innerWidth * 0.75 &&
              r.height > window.innerHeight * 0.45 &&
              (Number.isNaN(z) || z >= 20),
          };
        })
        .filter(x => x.score)
        .slice(0, 12);

      return {
        title: document.title,
        htmlClass: html.className,
        bodyClass: body.className,
        htmlDataPage: html.getAttribute("data-ff-page"),
        bodyDataPage: body.getAttribute("data-ff-page"),
        bodySurface: body.getAttribute("data-ff-surface"),
        scrollHeight: document.scrollingElement?.scrollHeight || 0,
        clientHeight: document.scrollingElement?.clientHeight || 0,
        bodyOverflowY: getComputedStyle(body).overflowY,
        htmlOverflowY: getComputedStyle(html).overflowY,
        css,
        js,
        revealCount: revealNodes.length,
        hiddenReveal,
        blockers,
      };
    });

    const bad =
      report.htmlClass.includes("ff-no-js") ||
      report.hiddenReveal.length > 0 ||
      report.blockers.length > 0 ||
      pageErrors.length > 0;

    if (bad) failures++;

    console.log(`\n${bad ? "❌" : "✅"} ${surface}/${viewportName} ${status} ${url}`);
    console.log(`  page: ${report.htmlDataPage || report.bodyDataPage || report.bodySurface || "-"}`);
    console.log(`  htmlClass: ${report.htmlClass}`);
    console.log(`  css: ${report.css.join(", ") || "none"}`);
    console.log(`  js: ${report.js.join(", ") || "none"}`);
    console.log(`  scroll: ${report.clientHeight}/${report.scrollHeight} overflow html/body: ${report.htmlOverflowY}/${report.bodyOverflowY}`);
    console.log(`  reveal: ${report.revealCount}, hidden/idle: ${report.hiddenReveal.length}`);
    console.log(`  blockers: ${report.blockers.length}`);

    if (report.hiddenReveal.length) {
      console.log("  hidden reveal sample:");
      console.log(JSON.stringify(report.hiddenReveal.slice(0, 5), null, 2));
    }

    if (report.blockers.length) {
      console.log("  blocker sample:");
      console.log(JSON.stringify(report.blockers.slice(0, 5), null, 2));
    }

    if (pageErrors.length) {
      console.log("  page errors:");
      console.log(pageErrors.map(x => `    - ${x}`).join("\n"));
    }

    if (consoleErrors.length) {
      console.log("  console warnings/errors:");
      console.log(consoleErrors.slice(0, 8).map(x => `    - ${x}`).join("\n"));
    }

    if (failedRequests.length) {
      console.log("  failed requests:");
      console.log(failedRequests.slice(0, 8).map(x => `    - ${x}`).join("\n"));
    }

    await page.close();
  }
}

await browser.close();

if (failures) {
  console.log(`\nIdle surface audit: FAIL (${failures} flagged viewport(s))`);
  process.exit(1);
}

console.log("\nIdle surface audit: PASS");

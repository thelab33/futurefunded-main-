import { chromium } from "playwright";
import fs from "node:fs";

const url = process.env.HOME_URL || process.env.FF_HOME_URL || "http://127.0.0.1:5000/platform/";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });

await page.goto(`${url}${url.includes("?") ? "&" : "?"}css_v=overflow-audit-${Date.now()}`, {
  waitUntil: "networkidle",
});

const report = await page.evaluate(() => {
  const vw = window.innerWidth;
  const doc = document.documentElement;
  const body = document.body;

  function selectorFor(el) {
    if (!el || el.nodeType !== 1) return "";
    const id = el.id ? `#${el.id}` : "";
    const cls = String(el.className || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 5)
      .map((c) => `.${CSS.escape(c)}`)
      .join("");
    return `${el.tagName.toLowerCase()}${id}${cls}`;
  }

  const offenders = [...document.querySelectorAll("body *")]
    .map((el) => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const overflowRight = Math.ceil(r.right - vw);
      const overflowLeft = Math.ceil(0 - r.left);

      return {
        selector: selectorFor(el),
        text: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 100),
        left: Math.round(r.left),
        right: Math.round(r.right),
        width: Math.round(r.width),
        overflowRight,
        overflowLeft,
        display: cs.display,
        position: cs.position,
        overflowX: cs.overflowX,
        gridTemplateColumns: cs.gridTemplateColumns,
      };
    })
    .filter((x) => x.overflowRight > 1 || x.overflowLeft > 1)
    .sort(
      (a, b) =>
        Math.max(b.overflowRight, b.overflowLeft) - Math.max(a.overflowRight, a.overflowLeft)
    )
    .slice(0, 30);

  return {
    url: location.href,
    innerWidth: vw,
    documentScrollWidth: doc.scrollWidth,
    bodyScrollWidth: body.scrollWidth,
    overflowX: Math.max(doc.scrollWidth, body.scrollWidth) - vw,
    offenders,
  };
});

fs.mkdirSync("artifacts/frontend-screenshots", { recursive: true });
fs.writeFileSync(
  "artifacts/frontend-screenshots/platform-overflow-audit.json",
  JSON.stringify(report, null, 2)
);

console.log(JSON.stringify(report, null, 2));
await browser.close();

if (report.overflowX > 0) {
  process.exitCode = 1;
}

import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || "";
const url = `${base}/platform/onboarding?operator_token=${encodeURIComponent(token)}&debug_v=onboarding-contract`;

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1300 } });

await page.goto(url, { waitUntil: "networkidle" });

const result = await page.evaluate(async () => {
  const requiredSelectors = {
    htmlPage: 'html[data-ff-page="platform-onboarding"]',
    body: "body.ff-onboardModernBody",
    shell: ".ff-onboardModernShell",
    header: ".ff-onboardModernHeader",
    main: '.ff-onboardModernMain[data-ff-surface-root="onboarding"]',
    hero: ".ff-onboardModernHero",
    form: '#ff-launch-setup-form[data-ff-contract="operator-launch-setup"]',
    pageCss: 'link[data-ff-page-css="onboarding.css"]',
  };

  const missing = Object.entries(requiredSelectors)
    .filter(([, selector]) => !document.querySelector(selector))
    .map(([name, selector]) => ({ name, selector }));

  const header = document.querySelector(".ff-onboardModernHeader");
  const hero = document.querySelector(".ff-onboardModernHero");
  const cssLink = document.querySelector('link[data-ff-page-css="onboarding.css"]');

  let headerToHero = null;

  if (header && hero) {
    const h = header.getBoundingClientRect();
    const he = hero.getBoundingClientRect();
    headerToHero = Math.round(he.top - h.bottom);
  }

  let cssHasMarker = false;
  const cssHref = cssLink?.href || null;

  if (cssHref) {
    const css = await fetch(cssHref).then((res) => res.text());
    cssHasMarker =
      css.includes("FF_ONBOARDING_AUTHORITY_V3_START") &&
      css.includes("FF_ONBOARDING_AUTHORITY_V3_END") &&
      css.includes("ff-onboardModernShell");
  }

  return {
    ok:
      missing.length === 0 &&
      cssHasMarker &&
      headerToHero !== null &&
      headerToHero >= 0 &&
      headerToHero <= 56,
    missing,
    cssHref,
    cssHasMarker,
    headerToHero,
  };
});

await browser.close();

console.log(JSON.stringify(result, null, 2));

if (!result.ok) {
  process.exitCode = 1;
}

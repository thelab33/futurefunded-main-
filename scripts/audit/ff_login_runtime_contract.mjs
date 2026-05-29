import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const url = `${base}/platform/login?debug_v=login-contract`;

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1300 } });

await page.goto(url, { waitUntil: "networkidle" });

const result = await page.evaluate(async () => {
  const requiredSelectors = {
    htmlPage: 'html[data-ff-page="platform-login"]',
    body: "body.ff-loginV4Body",
    root: '.ff-loginV4[data-ff-login-root="true"]',
    topbar: ".ff-loginV4__topbar",
    stage: ".ff-loginV4__stage",
    hero: ".ff-loginV4__hero",
    card: ".ff-loginV4__card[data-ff-login-card]",
    form: "#login-form[data-ff-login-form]",
    email: "[data-ff-login-email]",
    password: "[data-ff-login-password]",
    passwordToggle: "[data-ff-login-password-toggle]",
    submit: "[data-ff-login-submit]",
    pageCss: 'link[data-ff-page-css="login.css"]',
  };

  const missing = Object.entries(requiredSelectors)
    .filter(([, selector]) => !document.querySelector(selector))
    .map(([name, selector]) => ({ name, selector }));

  const ffCss = [...document.querySelectorAll('link[rel="stylesheet"]')].find((link) =>
    link.getAttribute("href")?.includes("/static/css/ff.css")
  );
  const loginCss = document.querySelector('link[data-ff-page-css="login.css"]');

  const links = [...document.querySelectorAll('link[rel="stylesheet"]')];
  const ffIndex = ffCss ? links.indexOf(ffCss) : -1;
  const loginIndex = loginCss ? links.indexOf(loginCss) : -1;
  const cssLoadsAfterFf = ffIndex >= 0 && loginIndex >= 0 && loginIndex > ffIndex;

  let cssHasMarker = false;
  const cssHref = loginCss?.href || null;

  if (cssHref) {
    const css = await fetch(cssHref).then((res) => res.text());
    cssHasMarker =
      css.includes("FF_LOGIN_AUTHORITY_V1_START") &&
      css.includes("FF_LOGIN_AUTHORITY_V1_END") &&
      css.includes("body.ff-loginV4Body") &&
      !css.includes("body.ff-loginStandaloneBody");
  }

  const bodyWidth = document.documentElement.clientWidth;
  const scrollWidth = document.documentElement.scrollWidth;
  const overflowX = scrollWidth > bodyWidth + 2;

  const topbar = document.querySelector(".ff-loginV4__topbar");
  const stage = document.querySelector(".ff-loginV4__stage");
  let topbarToStage = null;

  if (topbar && stage) {
    const t = topbar.getBoundingClientRect();
    const s = stage.getBoundingClientRect();
    topbarToStage = Math.round(s.top - t.bottom);
  }

  return {
    ok:
      missing.length === 0 &&
      cssLoadsAfterFf &&
      cssHasMarker &&
      !overflowX &&
      topbarToStage !== null &&
      topbarToStage >= 0 &&
      topbarToStage <= 28,
    missing,
    cssHref,
    cssLoadsAfterFf,
    cssHasMarker,
    overflowX,
    topbarToStage,
  };
});

await browser.close();

console.log(JSON.stringify(result, null, 2));

if (!result.ok) {
  process.exitCode = 1;
}

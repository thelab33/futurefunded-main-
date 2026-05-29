/* hoi_9i_login_proof — FutureFunded login contract proof */
import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const url = `${base.replace(/\/$/, "")}/platform/login`;

const viewports = [
  { name: "mobile", width: 390, height: 844, isMobile: true },
  { name: "desktop", width: 1440, height: 1100, isMobile: false },
];

const failures = [];

function fail(label, details = "") {
  failures.push(details ? `${label}: ${details}` : label);
}

async function main() {
  const browser = await chromium.launch({ headless: true });

  for (const viewport of viewports) {
    const page = await browser.newPage({
      viewport: { width: viewport.width, height: viewport.height },
      isMobile: viewport.isMobile,
      deviceScaleFactor: viewport.isMobile ? 2 : 1,
    });

    await page.goto(url, { waitUntil: "networkidle" });

    const status = await page.evaluate(() => {
      const root = document.querySelector("[data-ff-login-root]");
      const form = document.querySelector("[data-ff-login-form]");
      const email = document.querySelector("[data-ff-login-email]");
      const password = document.querySelector("[data-ff-login-password]");
      const submit = document.querySelector("[data-ff-login-submit]");
      const toggle = document.querySelector("[data-ff-login-password-toggle]");
      const stage = document.querySelector(".ff-loginAuthority__stage");

      const doc = document.documentElement;
      const overflow = Math.max(0, doc.scrollWidth - doc.clientWidth);

      const rootRect = root?.getBoundingClientRect();
      const formRect = form?.getBoundingClientRect();
      const stageRect = stage?.getBoundingClientRect();

      return {
        title: document.title,
        h1: document.querySelector("h1")?.textContent?.replace(/\s+/g, " ").trim() || "",
        hasRoot: Boolean(root),
        hasForm: Boolean(form),
        formMethod: form?.getAttribute("method") || "",
        formAction: form?.getAttribute("action") || "",
        hasEmail: Boolean(email),
        emailName: email?.getAttribute("name") || "",
        emailAutocomplete: email?.getAttribute("autocomplete") || "",
        hasPassword: Boolean(password),
        passwordName: password?.getAttribute("name") || "",
        passwordAutocomplete: password?.getAttribute("autocomplete") || "",
        hasSubmit: Boolean(submit),
        hasToggle: Boolean(toggle),
        hasNext: Boolean(document.querySelector("input[name='next']")),
        hasCsrf: Boolean(document.querySelector("input[name='csrf_token']")),
        overflow,
        rootWidth: Math.round(rootRect?.width || 0),
        formWidth: Math.round(formRect?.width || 0),
        stageWidth: Math.round(stageRect?.width || 0),
      };
    });

    if (!status.hasRoot) fail(`${viewport.name} login root missing`);
    if (!status.hasForm) fail(`${viewport.name} login form missing`);
    if (status.formMethod.toLowerCase() !== "post")
      fail(`${viewport.name} form method`, status.formMethod);
    if (!status.formAction.includes("/platform") && !/(^|\/)login(?:$|[?#])/.test(status.formAction))
      fail(`${viewport.name} form action unexpected`, status.formAction);
    if (!status.hasEmail || status.emailName !== "email")
      fail(`${viewport.name} email contract`, JSON.stringify(status));
    if (!status.hasPassword || status.passwordName !== "password")
      fail(`${viewport.name} password contract`, JSON.stringify(status));
    if (!status.hasSubmit) fail(`${viewport.name} submit missing`);
    if (!status.hasToggle) fail(`${viewport.name} password toggle missing`);
    if (!status.hasNext) fail(`${viewport.name} next input missing`);
    if (status.overflow > 2) fail(`${viewport.name} horizontal overflow`, `${status.overflow}px`);
    if (!/campaign|clarity|workspace/i.test(status.h1))
      fail(`${viewport.name} h1 unexpected`, status.h1);

    await page.locator("[data-ff-login-password-toggle]").click({ force: true });
    const typeAfterToggle = await page.locator("[data-ff-login-password]").getAttribute("type");
    if (typeAfterToggle !== "text") {
      fail(`${viewport.name} password toggle did not reveal password`, String(typeAfterToggle));
    }

    await page.close();
  }

  await browser.close();

  if (failures.length) {
    console.error("\n❌ FutureFunded login proof failed\n");
    for (const item of failures) console.error(`- ${item}`);
    process.exit(1);
  }

  console.log("✅ FutureFunded login proof passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

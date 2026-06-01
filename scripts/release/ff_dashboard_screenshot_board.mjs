#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "../..");

const baseUrl = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const loginEmail = process.env.FF_LOCAL_OPERATOR_EMAIL || "operator@getfuturefunded.local";
const loginPassword = process.env.FF_LOCAL_OPERATOR_PASSWORD || "FutureFunded!2026";
const strict = process.env.FF_DASHBOARD_BOARD_STRICT === "1";
const stamp = new Date().toISOString().replace(/[:.]/g, "-");

const outRoot = path.join(root, "audit_outputs/dashboard-screenshot-board", stamp);
const latest = path.join(root, "audit_outputs/dashboard-screenshot-board/latest");

const viewports = [
  { name: "mobile", width: 390, height: 1400 },
  { name: "tablet", width: 768, height: 1500 },
  { name: "desktop", width: 1440, height: 1100 },
];

const surfaces = [
  {
    key: "dashboard-locked",
    label: "Dashboard locked",
    type: "locked",
    path: "/platform/dashboard",
  },
  {
    key: "dashboard-session",
    label: "Dashboard session",
    type: "session",
    path: "/platform/dashboard",
  },
];

const esc = (value = "") => String(value).replace(/[&<>"]/g, (char) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  "\"": "&quot;",
}[char]));

async function warmPage(page) {
  const height = await page.evaluate(() => Math.max(
    document.documentElement.scrollHeight || 0,
    document.body.scrollHeight || 0,
    window.innerHeight || 0
  )).catch(() => 0);

  const viewportHeight = page.viewportSize()?.height || 900;
  const step = Math.max(320, Math.floor(viewportHeight * 0.72));

  for (let y = 0; y <= height + step; y += step) {
    await page.evaluate((scrollY) => window.scrollTo(0, scrollY), y).catch(() => {});
    await page.waitForTimeout(80).catch(() => {});
  }

  await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
  await page.waitForTimeout(180).catch(() => {});
}

async function performLogin(page) {
  await page.goto(`${baseUrl}/platform/login?dashboard_session_login=${Date.now()}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });

  await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});

  const emailSelector = 'input[type="email"], input[name*="email" i], input[id*="email" i]';
  const passwordSelector = 'input[type="password"], input[name*="password" i], input[id*="password" i]';

  await page.fill(emailSelector, loginEmail, { timeout: 12000 });
  await page.fill(passwordSelector, loginPassword, { timeout: 12000 });

  const submit = page.locator('button[type="submit"], input[type="submit"], button:has-text("Sign in"), button:has-text("Sign in securely")').first();
  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {}),
    submit.click({ timeout: 12000 }),
  ]);

  await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
}

async function capture(browser, surface, viewport) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });

  const page = await context.newPage();
  const pageErrors = [];
  const requestFailures = [];

  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    const url = request.url();
    if (/analytics|googletagmanager|hotjar|facebook|intercom|stripe/i.test(url)) return;
    requestFailures.push(`${request.failure()?.errorText || "request failed"}: ${url}`);
  });

  if (surface.type === "session") {
    await performLogin(page);
  }

  const joiner = surface.path.includes("?") ? "&" : "?";
  const url = `${baseUrl}${surface.path}${joiner}dashboard_board=${Date.now()}-${surface.key}-${viewport.name}`;
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });

  await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
  await warmPage(page);

  const screenshotName = `${surface.key}-${viewport.name}-full.png`;

  await page.screenshot({
    path: path.join(outRoot, screenshotName),
    fullPage: true,
    animations: "disabled",
  });

  const audit = await page.evaluate((surfaceType) => {
    const html = document.documentElement;
    const body = document.body;

    const visible = (node) => {
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };

    const ids = Array.from(document.querySelectorAll("[id]")).map((el) => el.id).filter(Boolean);
    const duplicateIds = Array.from(new Set(ids.filter((id, index) => ids.indexOf(id) !== index)));

    const brokenImages = Array.from(document.images)
      .filter((img) => visible(img))
      .filter((img) => !img.complete || img.naturalWidth === 0)
      .map((img) => ({ src: img.currentSrc || img.src, alt: img.alt || "" }));

    const actions = Array.from(document.querySelectorAll("a,button"))
      .filter(visible)
      .map((el) => ({
        text: (el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 90),
        href: el.getAttribute("href") || "",
        type: el.tagName.toLowerCase(),
      }))
      .filter((item) => item.text)
      .slice(0, 28);

    const fields = Array.from(document.querySelectorAll("input,textarea,select"))
      .filter(visible)
      .map((el) => ({
        name: el.getAttribute("name") || "",
        id: el.id || "",
        type: el.getAttribute("type") || el.tagName.toLowerCase(),
        placeholder: el.getAttribute("placeholder") || "",
        label: el.closest("label")?.innerText.trim().replace(/\s+/g, " ").slice(0, 90) || "",
      }));

    const sections = Array.from(document.querySelectorAll("main section, main article, main aside, main form, main details"))
      .filter(visible)
      .map((section) => {
        const heading = section.querySelector("h1,h2,h3,summary,legend");
        return {
          id: section.id || "",
          className: typeof section.className === "string" ? section.className : "",
          heading: heading ? heading.textContent.trim().replace(/\s+/g, " ").slice(0, 120) : "",
          height: Math.round(section.getBoundingClientRect().height),
        };
      })
      .slice(0, 36);

    const text = body.innerText || "";

    const common = {
      main: !!document.querySelector("main"),
      header: !!document.querySelector("[data-ff-header]"),
    };

    const lockedContracts = {
      gateRoot: !!document.querySelector("[data-ff-login-flagship], .ff-loginAuthority__shell, .ff-loginAuthority, [data-ff-dashboard-locked-root]"),
      gateMain: !!document.querySelector("main"),
      loginAction: !!document.querySelector('form, input[type="password"], a[href*="/platform/login"]'),
      noOperatorRoot: !document.querySelector("[data-ff-dashboard-root]"),
      protectedCopy: /operator access|required|protected dashboard|secure sign in|access the workspace|run the campaign with clarity/i.test(text),
    };

    const sessionContracts = {
      dashboardRoot: !!document.querySelector("[data-ff-dashboard-root]"),
      operatorRoot: !!document.querySelector("[data-ff-operator-root]") || document.body.hasAttribute("data-ff-operator-root"),
      ledgerUrl: document.body.hasAttribute("data-ff-ledger-url") && !!document.body.getAttribute("data-ff-ledger-url"),
      eventsUrl: document.body.hasAttribute("data-ff-events-url") && !!document.body.getAttribute("data-ff-events-url"),
      exportUrl: document.body.hasAttribute("data-ff-export-url") && !!document.body.getAttribute("data-ff-export-url"),
      exportHref: document.body.hasAttribute("data-ff-export-href") && !!document.body.getAttribute("data-ff-export-href"),
      publicCampaignAction: !!document.querySelector('a[href*="/c/"]'),
      setupAction: !!document.querySelector('a[href*="/platform/onboarding"]'),
      recordsSection: !!document.querySelector("[data-ff-operator-records]"),
      offlineForm: !!document.querySelector("[data-ff-offline-donation-form]"),
      dashboardJs: !!document.querySelector("[data-ff-operator-dashboard-js], script[src*='ff-operator-dashboard.js']"),
      execAssistant: !!document.querySelector("[data-ff-dashboard-exec-assistant-slot]"),
      operations: !!document.querySelector("[data-ff-dashboard-operations]"),
    };

    return {
      title: document.title,
      h1: document.querySelector("h1")?.textContent.trim().replace(/\s+/g, " ") || "",
      htmlPage: html.getAttribute("data-ff-page") || "",
      bodyPage: body.getAttribute("data-ff-page") || "",
      bodySurface: body.getAttribute("data-ff-surface") || "",
      height: Math.max(html.scrollHeight, body.scrollHeight),
      overflowX: Math.max(0, html.scrollWidth - html.clientWidth, body.scrollWidth - body.clientWidth),
      duplicateIds,
      brokenImages,
      actions,
      fields,
      sections,
      contracts: {
        ...common,
        ...(surfaceType === "locked" ? lockedContracts : sessionContracts),
      },
    };
  }, surface.type);

  await context.close();

  return {
    surface,
    viewport,
    url,
    status: response?.status() || null,
    screenshotName,
    pageErrors,
    requestFailures,
    audit,
  };
}

function failuresFor(result) {
  const failures = [];

  if (!result.status || result.status < 200 || result.status >= 400) failures.push(`HTTP ${result.status}`);
  if (!result.audit.h1) failures.push("missing H1");
  if (result.audit.overflowX > 2) failures.push(`horizontal overflow ${result.audit.overflowX}px`);
  if (result.audit.duplicateIds.length) failures.push(`duplicate IDs: ${result.audit.duplicateIds.join(", ")}`);
  if (result.audit.brokenImages.length) failures.push(`broken images: ${result.audit.brokenImages.length}`);
  if (result.pageErrors.length) failures.push(`page errors: ${result.pageErrors.length}`);
  if (result.requestFailures.length) failures.push(`request failures: ${result.requestFailures.length}`);

  if (result.surface.type === "session" && result.audit.sections.length < 6) {
    failures.push(`expected richer operator dashboard sections, found ${result.audit.sections.length}`);
  }

  for (const [name, ok] of Object.entries(result.audit.contracts)) {
    if (!ok) failures.push(`missing contract ${name}`);
  }

  return failures;
}

function reportMd(results) {
  const lines = [
    "# FutureFunded Dashboard Screenshot Board",
    "",
    `Generated: ${new Date().toISOString()}`,
    `Base URL: ${baseUrl}`,
    `Strict: ${strict ? "yes" : "no"}`,
    "",
  ];

  for (const result of results) {
    const failures = failuresFor(result);
    lines.push(`## ${result.surface.label} / ${result.viewport.name} — ${result.viewport.width}×${result.viewport.height}`);
    lines.push("");
    lines.push(`- URL: ${result.url}`);
    lines.push(`- Status: ${result.status}`);
    lines.push(`- Verdict: ${failures.length ? "REVIEW" : "PASS"}`);
    lines.push(`- H1: ${result.audit.h1 || "(missing)"}`);
    lines.push(`- Height: ${result.audit.height}px`);
    lines.push(`- Horizontal overflow: ${result.audit.overflowX}px`);
    lines.push(`- Sections: ${result.audit.sections.length}`);
    lines.push(`- Fields: ${result.audit.fields.length}`);
    lines.push(`- Actions: ${result.audit.actions.length}`);
    lines.push(`- Screenshot: ${result.screenshotName}`);
    if (failures.length) lines.push(`- Findings: ${failures.join("; ")}`);
    lines.push("");
  }

  return lines.join("\n");
}

function boardHtml(results) {
  const groups = surfaces.map((surface) => {
    const cards = results
      .filter((result) => result.surface.key === surface.key)
      .map((result) => {
        const failures = failuresFor(result);

        const sections = result.audit.sections.slice(0, 14).map((section) => `
          <li><strong>${esc(section.id || section.className || "section")}</strong><span>${esc(section.heading || "No heading")}</span><em>${section.height}px</em></li>
        `).join("");

        const fields = result.audit.fields.slice(0, 12).map((field) => `
          <li><strong>${esc(field.name || field.id || field.type)}</strong><span>${esc(field.label || field.placeholder || field.type)}</span></li>
        `).join("");

        const actions = result.audit.actions.slice(0, 12).map((action) => `
          <li><strong>${esc(action.text)}</strong><span>${esc(action.href || action.type)}</span></li>
        `).join("");

        return `
          <article class="card">
            <header>
              <div>
                <p>${esc(result.viewport.name)} / ${result.viewport.width}×${result.viewport.height}</p>
                <h2>${failures.length ? "Review needed" : "Ready"}</h2>
              </div>
              <span class="badge ${failures.length ? "bad" : "good"}">${failures.length ? "REVIEW" : "PASS"}</span>
            </header>
            <a href="${esc(result.screenshotName)}" target="_blank" rel="noreferrer">
              <img src="${esc(result.screenshotName)}" alt="FutureFunded ${esc(surface.label)} ${esc(result.viewport.name)} screenshot">
            </a>
            <section class="facts">
              <div><strong>${esc(result.audit.h1 || "Missing H1")}</strong><span>Primary headline</span></div>
              <div><strong>${result.audit.height}px</strong><span>Page height</span></div>
              <div><strong>${result.audit.sections.length}</strong><span>Sections</span></div>
              <div><strong>${result.audit.overflowX}px</strong><span>Horizontal overflow</span></div>
            </section>
            ${failures.length ? `<section class="issues"><h3>Findings</h3><ul>${failures.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></section>` : ""}
            <section class="lists"><h3>Sections</h3><ul>${sections || "<li><strong>No sections captured</strong><span></span></li>"}</ul></section>
            <section class="lists"><h3>Fields</h3><ul>${fields || "<li><strong>No visible fields</strong><span></span></li>"}</ul></section>
            <section class="lists"><h3>Actions</h3><ul>${actions || "<li><strong>No actions captured</strong><span></span></li>"}</ul></section>
          </article>
        `;
      }).join("");

    return `
      <section class="surfaceGroup">
        <div class="surfaceTitle">
          <p>FutureFunded dashboard surface</p>
          <h2>${esc(surface.label)}</h2>
          <span>${esc(surface.type === "session" ? "login → /platform/dashboard" : "/platform/dashboard")}</span>
        </div>
        <div class="grid">${cards}</div>
      </section>
    `;
  }).join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FutureFunded Dashboard Screenshot Board</title>
  <style>
    :root { --ink:#17120d; --muted:rgba(23,18,13,.62); --line:rgba(61,43,24,.14); --card:rgba(255,255,255,.9); --good:#176b4d; --bad:#9b2f24; }
    * { box-sizing:border-box; }
    body { margin:0; font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:linear-gradient(180deg,#fffaf2,#efe0c8); }
    .shell { width:min(1480px, calc(100% - 28px)); margin-inline:auto; padding:34px 0 64px; }
    .hero, .surfaceTitle { display:flex; justify-content:space-between; gap:24px; align-items:flex-end; padding:24px; border:1px solid var(--line); border-radius:28px; background:rgba(255,255,255,.72); box-shadow:0 24px 80px rgba(30,21,12,.10); }
    .hero p, .surfaceTitle p, .card header p { margin:0 0 8px; color:var(--muted); font-weight:780; text-transform:uppercase; letter-spacing:.12em; font-size:12px; }
    h1 { margin:0; max-width:820px; font-size:clamp(36px,6vw,82px); line-height:.92; letter-spacing:-.07em; }
    .meta, .surfaceTitle span { color:var(--muted); text-align:right; }
    .surfaceGroup { margin-top:24px; }
    .surfaceTitle h2 { margin:0; font-size:clamp(28px,4vw,52px); line-height:.95; letter-spacing:-.06em; }
    .grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:18px; margin-top:18px; align-items:start; }
    .card { border:1px solid var(--line); border-radius:26px; background:var(--card); box-shadow:0 18px 65px rgba(30,21,12,.09); overflow:hidden; }
    .card header { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:18px; border-bottom:1px solid var(--line); }
    .card h2 { margin:0; font-size:22px; letter-spacing:-.035em; }
    .badge { display:inline-flex; align-items:center; justify-content:center; min-width:76px; height:34px; border-radius:999px; color:white; font-weight:850; font-size:11px; letter-spacing:.09em; }
    .badge.good { background:var(--good); }
    .badge.bad { background:var(--bad); }
    img { display:block; width:100%; height:520px; object-fit:cover; object-position:top center; border-bottom:1px solid var(--line); background:#eee; }
    .facts { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1px; background:var(--line); }
    .facts div { padding:14px; background:rgba(255,255,255,.72); }
    .facts strong { display:block; font-size:14px; letter-spacing:-.02em; }
    .facts span { display:block; color:var(--muted); font-size:12px; margin-top:2px; }
    .issues, .lists { padding:16px 18px; border-top:1px solid var(--line); }
    h3 { margin:0 0 10px; font-size:13px; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); }
    ul { list-style:none; padding:0; margin:0; display:grid; gap:8px; }
    li { display:flex; justify-content:space-between; gap:10px; border:1px solid rgba(61,43,24,.10); border-radius:14px; padding:10px; background:rgba(255,250,242,.58); }
    li strong { font-size:13px; }
    li span, li em { color:var(--muted); font-size:12px; font-style:normal; text-align:right; }
    .issues li { color:var(--bad); border-color:rgba(155,47,36,.18); background:rgba(155,47,36,.06); }
    @media (max-width:1100px) { .grid { grid-template-columns:1fr; } img { height:auto; max-height:760px; } .hero, .surfaceTitle { align-items:flex-start; flex-direction:column; } .meta, .surfaceTitle span { text-align:left; } }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div>
        <p>FutureFunded operator workspace</p>
        <h1>Dashboard screenshot board</h1>
      </div>
      <div class="meta">${esc(baseUrl)}/platform/dashboard<br>${esc(new Date().toISOString())}</div>
    </section>
    ${groups}
  </main>
</body>
</html>`;
}

async function main() {
  await fs.mkdir(outRoot, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const results = [];

  try {
    for (const surface of surfaces) {
      for (const viewport of viewports) {
        console.log(`Auditing ${surface.label} / ${viewport.name} → ${baseUrl}${surface.path}`);
        results.push(await capture(browser, surface, viewport));
      }
    }
  } finally {
    await browser.close();
  }

  await fs.writeFile(path.join(outRoot, "report.json"), JSON.stringify({ generatedAt: new Date().toISOString(), baseUrl, strict, results }, null, 2));
  await fs.writeFile(path.join(outRoot, "report.md"), reportMd(results));
  await fs.writeFile(path.join(outRoot, "index.html"), boardHtml(results));

  await fs.rm(latest, { recursive: true, force: true });
  await fs.mkdir(path.dirname(latest), { recursive: true });
  await fs.symlink(outRoot, latest, "dir").catch(async () => {
    await fs.cp(outRoot, latest, { recursive: true });
  });

  const failures = results.flatMap((result) => failuresFor(result).map((failure) => `${result.surface.label} / ${result.viewport.name}: ${failure}`));

  console.log("");
  console.log("FutureFunded dashboard screenshot board complete");
  console.log("================================================");
  console.log(`Output: ${outRoot}`);
  console.log(`Latest: ${latest}`);
  console.log(`Report: ${path.join(latest, "report.md")}`);
  console.log(`Open board: python3 -m http.server 8770 --directory ${latest}`);
  console.log(`Then open:  http://127.0.0.1:8770/index.html`);

  if (failures.length) {
    console.log("");
    console.log("Review findings:");
    for (const failure of failures) console.log(`- ${failure}`);
    if (strict) process.exitCode = 1;
  } else {
    console.log("");
    console.log("✅ Dashboard board passed locked/session mobile/tablet/desktop checks.");
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

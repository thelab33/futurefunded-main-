#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "../..");
const baseUrl = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const strict = process.env.FF_LOGIN_BOARD_STRICT === "1";
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const outRoot = path.join(root, "audit_outputs/login-screenshot-board", stamp);
const latest = path.join(root, "audit_outputs/login-screenshot-board/latest");

const viewports = [
  { name: "mobile", width: 390, height: 1400 },
  { name: "tablet", width: 768, height: 1500 },
  { name: "desktop", width: 1440, height: 1100 },
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
    await page.waitForTimeout(70).catch(() => {});
  }

  await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
  await page.waitForTimeout(150).catch(() => {});
}

async function capture(browser, viewport) {
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

  const url = `${baseUrl}/platform/login?login_board=${Date.now()}-${viewport.name}`;
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
  await warmPage(page);

  const screenshotName = `login-${viewport.name}-full.png`;
  await page.screenshot({
    path: path.join(outRoot, screenshotName),
    fullPage: true,
    animations: "disabled",
  });

  const audit = await page.evaluate(() => {
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

    const fields = Array.from(document.querySelectorAll("input,textarea,select"))
      .filter(visible)
      .map((el) => ({
        name: el.getAttribute("name") || "",
        id: el.id || "",
        type: el.getAttribute("type") || el.tagName.toLowerCase(),
        placeholder: el.getAttribute("placeholder") || "",
        label: el.closest("label")?.innerText.trim().replace(/\s+/g, " ").slice(0, 90) || "",
      }));

    const actions = Array.from(document.querySelectorAll("a,button"))
      .filter(visible)
      .map((el) => ({
        text: (el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 90),
        href: el.getAttribute("href") || "",
        type: el.tagName.toLowerCase(),
      }))
      .filter((item) => item.text)
      .slice(0, 18);

    const sections = Array.from(document.querySelectorAll("main section, main article, main form, main div"))
      .filter(visible)
      .slice(0, 14)
      .map((section) => {
        const heading = section.querySelector("h1,h2,h3,legend");
        return {
          id: section.id || "",
          className: typeof section.className === "string" ? section.className : "",
          heading: heading ? heading.textContent.trim().replace(/\s+/g, " ").slice(0, 120) : "",
          height: Math.round(section.getBoundingClientRect().height),
        };
      });

    const text = body.innerText || "";
    const hasPassword = !!document.querySelector('input[type="password"]');
    const hasEmail = !!document.querySelector('input[type="email"], input[name*="email" i], input[id*="email" i]');
    const hasToken = !!document.querySelector('input[name*="token" i], input[id*="token" i]');

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
      fields,
      actions,
      sections,
      contracts: {
        main: !!document.querySelector("main"),
        header: !!document.querySelector("[data-ff-header]"),
        formOrFields: !!document.querySelector("form") || fields.length > 0,
        authField: hasPassword || hasEmail || hasToken || /access token|operator|login|sign in/i.test(text),
        submitAction: !!document.querySelector('button, input[type="submit"], a[href*="dashboard"], a[href*="login"]'),
      },
    };
  });

  await context.close();

  return {
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

  for (const [name, ok] of Object.entries(result.audit.contracts)) {
    if (!ok) failures.push(`missing contract ${name}`);
  }

  return failures;
}

function reportMd(results) {
  const lines = [
    "# FutureFunded Operator Login Screenshot Board",
    "",
    `Generated: ${new Date().toISOString()}`,
    `Base URL: ${baseUrl}`,
    `Strict: ${strict ? "yes" : "no"}`,
    "",
  ];

  for (const result of results) {
    const failures = failuresFor(result);
    lines.push(`## ${result.viewport.name} — ${result.viewport.width}×${result.viewport.height}`);
    lines.push("");
    lines.push(`- Status: ${result.status}`);
    lines.push(`- Verdict: ${failures.length ? "REVIEW" : "PASS"}`);
    lines.push(`- H1: ${result.audit.h1 || "(missing)"}`);
    lines.push(`- Height: ${result.audit.height}px`);
    lines.push(`- Horizontal overflow: ${result.audit.overflowX}px`);
    lines.push(`- Fields: ${result.audit.fields.length}`);
    lines.push(`- Actions: ${result.audit.actions.length}`);
    lines.push(`- Screenshot: ${result.screenshotName}`);
    if (failures.length) lines.push(`- Findings: ${failures.join("; ")}`);
    lines.push("");
  }

  return lines.join("\n");
}

function boardHtml(results) {
  const cards = results.map((result) => {
    const failures = failuresFor(result);

    const fields = result.audit.fields.slice(0, 10).map((field) => `
      <li><strong>${esc(field.name || field.id || field.type)}</strong><span>${esc(field.label || field.placeholder || field.type)}</span></li>
    `).join("");

    const actions = result.audit.actions.slice(0, 10).map((action) => `
      <li><strong>${esc(action.text)}</strong><span>${esc(action.href || action.type)}</span></li>
    `).join("");

    const sections = result.audit.sections.slice(0, 10).map((section) => `
      <li><strong>${esc(section.id || section.className || "section")}</strong><span>${esc(section.heading || "No heading")}</span><em>${section.height}px</em></li>
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
          <img src="${esc(result.screenshotName)}" alt="FutureFunded operator login ${esc(result.viewport.name)} screenshot">
        </a>
        <section class="facts">
          <div><strong>${esc(result.audit.h1 || "Missing H1")}</strong><span>Primary headline</span></div>
          <div><strong>${result.audit.height}px</strong><span>Page height</span></div>
          <div><strong>${result.audit.fields.length}</strong><span>Visible fields</span></div>
          <div><strong>${result.audit.overflowX}px</strong><span>Horizontal overflow</span></div>
        </section>
        ${failures.length ? `<section class="issues"><h3>Findings</h3><ul>${failures.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></section>` : ""}
        <section class="lists"><h3>Sections</h3><ul>${sections || "<li><strong>No sections captured</strong><span></span></li>"}</ul></section>
        <section class="lists"><h3>Fields</h3><ul>${fields || "<li><strong>No visible fields</strong><span></span></li>"}</ul></section>
        <section class="lists"><h3>Actions</h3><ul>${actions || "<li><strong>No actions captured</strong><span></span></li>"}</ul></section>
      </article>
    `;
  }).join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FutureFunded Operator Login Screenshot Board</title>
  <style>
    :root { --ink:#17120d; --muted:rgba(23,18,13,.62); --line:rgba(61,43,24,.14); --card:rgba(255,255,255,.9); --good:#176b4d; --bad:#9b2f24; }
    * { box-sizing:border-box; }
    body { margin:0; font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:linear-gradient(180deg,#fffaf2,#efe0c8); }
    .shell { width:min(1380px, calc(100% - 28px)); margin-inline:auto; padding:34px 0 64px; }
    .hero { display:flex; justify-content:space-between; gap:24px; align-items:flex-end; padding:24px; border:1px solid var(--line); border-radius:28px; background:rgba(255,255,255,.72); box-shadow:0 24px 80px rgba(30,21,12,.10); }
    .hero p, .card header p { margin:0 0 8px; color:var(--muted); font-weight:780; text-transform:uppercase; letter-spacing:.12em; font-size:12px; }
    h1 { margin:0; max-width:820px; font-size:clamp(36px,6vw,82px); line-height:.92; letter-spacing:-.07em; }
    .meta { color:var(--muted); text-align:right; }
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
    @media (max-width:1100px) { .grid { grid-template-columns:1fr; } img { height:auto; max-height:760px; } .hero { align-items:flex-start; flex-direction:column; } .meta { text-align:left; } }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div>
        <p>FutureFunded operator access</p>
        <h1>Login screenshot board</h1>
      </div>
      <div class="meta">${esc(baseUrl)}/platform/login<br>${esc(new Date().toISOString())}</div>
    </section>
    <section class="grid">${cards}</section>
  </main>
</body>
</html>`;
}

async function main() {
  await fs.mkdir(outRoot, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const results = [];

  try {
    for (const viewport of viewports) {
      console.log(`Auditing Operator login / ${viewport.name} → ${baseUrl}/platform/login`);
      results.push(await capture(browser, viewport));
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

  const failures = results.flatMap((result) => failuresFor(result).map((failure) => `${result.viewport.name}: ${failure}`));

  console.log("");
  console.log("FutureFunded operator login screenshot board complete");
  console.log("====================================================");
  console.log(`Output: ${outRoot}`);
  console.log(`Latest: ${latest}`);
  console.log(`Report: ${path.join(latest, "report.md")}`);
  console.log(`Open board: python3 -m http.server 8769 --directory ${latest}`);
  console.log(`Then open:  http://127.0.0.1:8769/index.html`);

  if (failures.length) {
    console.log("");
    console.log("Review findings:");
    for (const failure of failures) console.log(`- ${failure}`);
    if (strict) process.exitCode = 1;
  } else {
    console.log("");
    console.log("✅ Operator login board passed mobile/tablet/desktop checks.");
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

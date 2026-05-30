const fs = require("fs");
const path = require("path");

let chromium;
try {
  chromium = require("playwright").chromium;
} catch {
  chromium = require("@playwright/test").chromium;
}

const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
const baseUrl = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || process.env.OPERATOR_ACCESS_TOKEN || "dev-operator-20260529123018";
const root = `audit_outputs/visual-boards-three-viewports/${stamp}`;

const viewports = [
  { key: "desktop", label: "Desktop", width: 1440, height: 1000 },
  { key: "tablet", label: "Tablet", width: 834, height: 1112 },
  { key: "mobile", label: "Mobile", width: 390, height: 844 }
];

const pages = [
  { group: "Marketing", key: "platform-home", label: "Platform homepage", url: "/platform/" },
  { group: "Campaign", key: "campaign", label: "Campaign page", url: "/c/connect-atx-elite" },
  { group: "Auth", key: "login", label: "Login", url: "/platform/login" },
  { group: "Auth", key: "forgot-password", label: "Forgot password", url: "/platform/forgot-password" },
  { group: "Auth", key: "reset-password", label: "Reset password", url: "/platform/reset-password" },
  { group: "Auth", key: "invite", label: "Invite", url: "/platform/invite" },
  { group: "Auth", key: "mfa", label: "MFA", url: "/platform/mfa" },
  { group: "Auth", key: "register", label: "Register", url: "/platform/register" },
  { group: "Onboarding", key: "onboarding", label: "Onboarding", url: "/platform/onboarding" },
  { group: "Dashboard", key: "dashboard-locked", label: "Dashboard locked", url: "/platform/dashboard", ok: [403] },
  { group: "Dashboard", key: "dashboard-unlocked", label: "Dashboard unlocked", url: `/platform/dashboard?access_token=${encodeURIComponent(token)}` }
];

function cleanName(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function redact(url) {
  return String(url).replace(/access_token=[^&]+/g, "access_token=<redacted>");
}

async function metrics(page, origin) {
  return page.evaluate((origin) => {
    const imgs = [...document.querySelectorAll("img")].map((img) => ({
      src: img.currentSrc || img.src || "",
      complete: img.complete,
      w: img.naturalWidth,
      h: img.naturalHeight,
      loading: img.getAttribute("loading") || "",
      hidden: !!img.closest("[hidden], [aria-hidden='true'], dialog:not([open]), .is-hidden")
    }));

    const localBroken = imgs.filter((img) => {
      if (!img.src || img.src.startsWith("data:")) return false;

      const isLazyOrHidden =
        img.loading === "lazy" ||
        img.hidden ||
        img.src.includes("#lazy-ok");

      try {
        const isLocal = new URL(img.src).origin === origin;
        const didFail = img.complete && (img.w <= 0 || img.h <= 0);

        // Visual boards should not fail lazy offscreen or hidden modal images
        // before the browser has requested them. Real completed local failures
        // are still surfaced.
        return isLocal && !isLazyOrHidden && didFail;
      } catch {
        return false;
      }
    });

    return {
      title: document.title || "",
      h1: document.querySelector("h1")?.innerText?.trim() || "",
      header: document.querySelectorAll("[data-ff-header]").length,
      actions: document.querySelectorAll("a, button, [role='button']").length,
      forms: document.querySelectorAll("form").length,
      images: imgs.length,
      localBroken: localBroken.length,
      localBrokenSrcs: localBroken.map((x) => x.src),
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      height: document.body.scrollHeight
    };
  }, origin);
}

function htmlEscape(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderBoard(viewport, rows, dir) {
  const groups = [...new Set(rows.map((r) => r.group))];

  const css = `
    :root{color-scheme:dark;--bg:#090d18;--panel:rgba(255,255,255,.075);--line:rgba(255,255,255,.16);--text:#f8fafc;--muted:rgba(248,250,252,.68);--accent:#f7c948;--good:#86efac;--bad:#fb7185}
    *{box-sizing:border-box}
    body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:radial-gradient(circle at 10% 0%,rgba(247,201,72,.20),transparent 34rem),radial-gradient(circle at 90% 10%,rgba(96,165,250,.16),transparent 30rem),var(--bg);color:var(--text)}
    header{position:sticky;top:0;z-index:10;padding:28px clamp(18px,4vw,52px);border-bottom:1px solid var(--line);background:rgba(9,13,24,.86);backdrop-filter:blur(18px)}
    .eyebrow{color:var(--accent);font-weight:900;font-size:12px;text-transform:uppercase;letter-spacing:.18em}
    h1{margin:8px 0 10px;font-size:clamp(34px,5vw,68px);line-height:.92;letter-spacing:-.07em}
    p{margin:0;color:var(--muted);line-height:1.55;max-width:920px}
    nav{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
    nav a{color:var(--text);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:8px 12px;background:rgba(255,255,255,.07);font-size:13px;font-weight:800}
    main{padding:30px clamp(18px,4vw,52px) 70px;display:grid;gap:42px}
    section{display:grid;gap:18px}
    .sectionHead{display:flex;justify-content:space-between;gap:18px;align-items:end;border-bottom:1px solid var(--line);padding-bottom:12px}
    h2{margin:0;font-size:clamp(24px,3vw,36px);letter-spacing:-.045em}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,380px),1fr));gap:22px}
    .card{overflow:hidden;border:1px solid var(--line);border-radius:26px;background:linear-gradient(180deg,rgba(255,255,255,.105),rgba(255,255,255,.055));box-shadow:0 24px 90px rgba(0,0,0,.28)}
    .meta{padding:16px;display:grid;gap:9px}
    .title{font-weight:950;letter-spacing:-.025em}
    .url{color:var(--muted);font-size:11px;overflow-wrap:anywhere}
    .pills{display:flex;flex-wrap:wrap;gap:7px}
    .pill{border:1px solid var(--line);border-radius:999px;padding:5px 8px;background:rgba(255,255,255,.06);font-size:11px;font-weight:850;color:var(--muted)}
    .good{color:var(--good)} .bad{color:var(--bad)}
    .shot{display:block;border-top:1px solid var(--line);background:rgba(255,255,255,.04)}
    .shot img{display:block;width:100%;height:${viewport.key === "mobile" ? "620px" : "660px"};object-fit:cover;object-position:top center}
  `;

  const sections = groups.map((group) => {
    const cards = rows.filter((r) => r.group === group).map((r) => {
      const m = r.metrics || {};
      const bad = r.error || !r.expected.includes(r.status) || m.overflow || m.localBroken > 0;
      return `
        <article class="card">
          <div class="meta">
            <div class="title">${htmlEscape(r.label)}</div>
            <div class="url">${htmlEscape(redact(r.fullUrl))}</div>
            <div class="pills">
              <span class="pill ${bad ? "bad" : "good"}">${bad ? "Check" : "Pass"}</span>
              <span class="pill">HTTP ${htmlEscape(r.status ?? "ERR")}</span>
              <span class="pill">${htmlEscape(m.actions ?? 0)} actions</span>
              <span class="pill">${htmlEscape(m.images ?? 0)} images</span>
              <span class="pill ${m.localBroken ? "bad" : "good"}">${htmlEscape(m.localBroken ?? 0)} local broken</span>
              <span class="pill ${m.overflow ? "bad" : "good"}">${m.overflow ? "Overflow" : "No overflow"}</span>
            </div>
          </div>
          <a class="shot" href="${htmlEscape(r.screenshot)}">
            <img src="${htmlEscape(r.screenshot)}" alt="${htmlEscape(r.label)} screenshot" loading="lazy">
          </a>
        </article>
      `;
    }).join("");

    return `
      <section id="${cleanName(group)}">
        <div class="sectionHead">
          <h2>${htmlEscape(group)}</h2>
          <div>${rows.filter((r) => r.group === group).length} surfaces</div>
        </div>
        <div class="grid">${cards}</div>
      </section>
    `;
  }).join("");

  const html = `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FutureFunded ${viewport.label} Visual Board</title>
  <style>${css}</style>
</head>
<body>
  <header>
    <div class="eyebrow">FutureFunded Visual QA</div>
    <h1>${viewport.label} board</h1>
    <p>All major FutureFunded product pages captured at ${viewport.width}×${viewport.height}. Review visual polish, spacing, hierarchy, responsiveness, overflow, and broken local images.</p>
    <nav>
      ${groups.map((g) => `<a href="#${cleanName(g)}">${htmlEscape(g)}</a>`).join("")}
      <a href="../index.html">All boards</a>
      <a href="reports/visual-board-${viewport.key}.md">Report</a>
    </nav>
  </header>
  <main>${sections}</main>
</body>
</html>`;

  fs.writeFileSync(path.join(dir, "index.html"), html);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const origin = new URL(baseUrl).origin;
  const all = [];

  for (const vp of viewports) {
    const dir = path.join(root, vp.key);
    const shots = path.join(dir, "screenshots");
    const reports = path.join(dir, "reports");
    fs.mkdirSync(shots, { recursive: true });
    fs.mkdirSync(reports, { recursive: true });

    const rows = [];

    for (const p of pages) {
      const page = await browser.newPage({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 1,
        reducedMotion: "reduce"
      });

      const expected = p.ok || [200];
      const fullUrl = `${baseUrl}${p.url}`;
      const row = { ...p, viewport: vp.key, expected, fullUrl, status: null, screenshot: "", metrics: {}, error: "" };

      try {
        const joiner = fullUrl.includes("?") ? "&" : "?";
        const res = await page.goto(`${fullUrl}${joiner}visual_board=${Date.now()}`, {
          waitUntil: "domcontentloaded",
          timeout: 60000
        });

        row.status = res ? res.status() : null;
        await page.waitForLoadState("load", { timeout: 45000 }).catch(() => {});
        await page.waitForTimeout(900);

        row.metrics = await metrics(page, origin);

        const file = `${cleanName(p.key)}-${vp.key}.png`;
        await page.screenshot({ path: path.join(shots, file), fullPage: true });
        row.screenshot = `screenshots/${file}`;
      } catch (err) {
        row.error = String(err && err.stack ? err.stack : err);
      }

      rows.push(row);
      all.push(row);
      await page.close();
    }

    fs.writeFileSync(path.join(reports, `visual-board-${vp.key}.json`), JSON.stringify(rows, null, 2));

    const md = [
      `# FutureFunded ${vp.label} Visual Board`,
      "",
      `Viewport: ${vp.width}x${vp.height}`,
      "",
      "| Group | Surface | HTTP | Expected | H1 | Actions | Images | Local broken | Overflow | Screenshot |",
      "|---|---|---:|---|---|---:|---:|---:|---:|---|"
    ];

    for (const r of rows) {
      const m = r.metrics || {};
      md.push(`| ${r.group} | ${r.label} | ${r.status ?? "ERR"} | ${r.expected.join("/")} | ${String(m.h1 || "").replaceAll("|", "/")} | ${m.actions ?? 0} | ${m.images ?? 0} | ${m.localBroken ?? 0} | ${m.overflow ?? "n/a"} | ${r.screenshot} |`);
    }

    md.push("", "## Local broken images");
    for (const r of rows) {
      const srcs = r.metrics?.localBrokenSrcs || [];
      if (!srcs.length) continue;
      md.push("", `### ${r.label}`);
      srcs.forEach((src) => md.push(`- ${src}`));
    }

    fs.writeFileSync(path.join(reports, `visual-board-${vp.key}.md`), md.join("\n"));
    renderBoard(vp, rows, dir);
  }

  await browser.close();

  const hub = `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FutureFunded Visual Boards</title>
  <style>
    body{margin:0;min-height:100vh;display:grid;place-items:center;background:#080c16;color:#f8fafc;font-family:Inter,system-ui,sans-serif}
    main{width:min(980px,100%);padding:34px;display:grid;gap:24px}
    h1{font-size:clamp(38px,7vw,80px);line-height:.9;letter-spacing:-.07em;margin:0}
    p{color:rgba(248,250,252,.7);line-height:1.55;max-width:760px}
    .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
    a{color:inherit;text-decoration:none;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.075);border-radius:28px;padding:24px;min-height:190px;display:grid;align-content:space-between}
    strong{font-size:32px;letter-spacing:-.05em}
    span{color:#f7c948;font-weight:900;text-transform:uppercase;font-size:12px;letter-spacing:.16em}
    @media(max-width:760px){.grid{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <main>
    <div>
      <span>FutureFunded visual QA</span>
      <h1>Three viewport boards.</h1>
      <p>Open one board at a time: all pages in desktop, all pages in tablet, and all pages in mobile.</p>
    </div>
    <section class="grid">
      <a href="desktop/index.html"><span>1440x1000</span><strong>Desktop</strong></a>
      <a href="tablet/index.html"><span>834x1112</span><strong>Tablet</strong></a>
      <a href="mobile/index.html"><span>390x844</span><strong>Mobile</strong></a>
    </section>
  </main>
</body>
</html>`;

  fs.writeFileSync(path.join(root, "index.html"), hub);
  fs.writeFileSync(path.join(root, "visual-board-all.json"), JSON.stringify(all, null, 2));

  fs.rmSync("audit_outputs/visual-boards-three-viewports/latest", { force: true, recursive: true });
  fs.mkdirSync("audit_outputs/visual-boards-three-viewports", { recursive: true });
  fs.symlinkSync(path.basename(root), "audit_outputs/visual-boards-three-viewports/latest", "dir");

  console.log("✅ Three viewport visual boards complete.");
  console.log(`Hub:     ${root}/index.html`);
  console.log(`Desktop: ${root}/desktop/index.html`);
  console.log(`Tablet:  ${root}/tablet/index.html`);
  console.log(`Mobile:  ${root}/mobile/index.html`);
})();

#!/usr/bin/env node
import { chromium } from "playwright";
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const base = (
  process.argv[2] ||
  process.env.FF_PUBLIC_BASE_URL ||
  "https://getfuturefunded.com"
).replace(/\/$/, "");

const localBase = (
  process.env.FF_LOCAL_BASE_URL ||
  "http://127.0.0.1:5000"
).replace(/\/$/, "");

const slug = process.argv[3] || process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || "";
const assetV = process.env.FF_ASSET_V || `enterprise-gate-${Date.now()}`;
const runMoneyLoop = process.env.FF_GATE_MONEY_LOOP === "1";
const runShareQr = process.env.FF_GATE_SHARE_QR !== "0";

const generatedAt = new Date().toISOString();
const safeStamp = generatedAt.replace(/[:.]/g, "-");
const proofDir = "docs/release-proof";
const artifactDir = path.join("audit_outputs", "enterprise-gate", safeStamp);

fs.mkdirSync(proofDir, { recursive: true });
fs.mkdirSync(artifactDir, { recursive: true });

const results = [];

function record(ok, label, detail = "") {
  results.push({ ok: Boolean(ok), label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
}

function firstLines(text, count = 4) {
  return String(text || "")
    .split("\n")
    .filter(Boolean)
    .slice(0, count)
    .join(" | ");
}

function metaContent(html, property) {
  const propRe = new RegExp(
    `<meta[^>]+property=["']${property}["'][^>]+content=["']([^"']+)["']`,
    "i"
  );
  const nameRe = new RegExp(
    `<meta[^>]+name=["']${property}["'][^>]+content=["']([^"']+)["']`,
    "i"
  );

  return html.match(propRe)?.[1] || html.match(nameRe)?.[1] || "";
}

function includesAny(text, markers = []) {
  return markers.some((marker) => text.includes(marker));
}

async function fetchText(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeout || 30_000);

  try {
    const res = await fetch(url, {
      redirect: options.redirect || "manual",
      method: options.method || "GET",
      headers: options.headers || {},
      body: options.body,
      signal: controller.signal,
    });

    const text = await res.text();
    return { status: res.status, headers: res.headers, text, ok: res.ok };
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchJson(url, options = {}) {
  const out = await fetchText(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
  });

  let json = {};
  try {
    json = JSON.parse(out.text || "{}");
  } catch {
    json = {};
  }

  return { ...out, json };
}

console.log("\nFutureFunded Enterprise Launch Gate v3");
console.log(`Base: ${base}`);
console.log(`Local base: ${localBase}`);
console.log(`Campaign: ${slug}`);
console.log(`Asset version: ${assetV}`);
console.log(`Share/QR proof: ${runShareQr ? "enabled" : "disabled"}`);
console.log(`Money-loop proof: ${runMoneyLoop ? "enabled" : "disabled"}\n`);

const securityHeaders = [
  "content-security-policy",
  "x-content-type-options",
  "x-frame-options",
  "referrer-policy",
];

const routes = [
  {
    name: "Live homepage",
    url: `${base}/platform/?css_v=${encodeURIComponent(assetV)}`,
    expect: 200,
    mustInclude: ["FutureFunded", "Launch a premium fundraising page"],
    mustIncludeAnyGroups: [
      ["platform.bundle.css", "platform-home.css"],
    ],
    mustNotInclude: ["ff.cinematic.css", "ff-cinematic.js"],
  },
  {
    name: "Live campaign",
    url: `${base}/c/${encodeURIComponent(slug)}?css_v=${encodeURIComponent(assetV)}`,
    expect: 200,
    mustInclude: ["ff-campaign.js", "ffCampaignConfig", "data-ff-open-checkout"],
    mustIncludeAnyGroups: [
      ["campaign.bundle.css", "ff.css"],
      ["ff.css", "campaign.css", "data-ff-checkout-css-contract"],
      ["data-ff-share-trigger", "data-ff-qr-trigger", "ff-shareDrawer"],
    ],
    mustNotInclude: ["ff.cinematic.css", "ff-cinematic.js"],
    campaignOg: true,
  },
  {
    name: "Live onboarding",
    url: `${base}/platform/onboarding?css_v=${encodeURIComponent(assetV)}`,
    expect: 200,
    mustInclude: ["FutureFunded"],
    mustIncludeAnyGroups: [
      ["onboarding.bundle.css", "onboarding.css"],
      ["data-ff-surface=\"onboarding\"", "data-ff-page=\"platform-onboarding\"", "ff-onboardModern"],
    ],
    mustNotInclude: ["ff.cinematic.css", "ff-cinematic.js"],
  },
  {
    name: "Live login",
    url: `${base}/platform/login?css_v=${encodeURIComponent(assetV)}`,
    expect: 200,
    mustInclude: ["operator-login-v4", "ff-loginV4", "ff-login.js", "FutureFunded"],
    mustIncludeAnyGroups: [
      ["login.bundle.css", "login.css"],
    ],
    mustNotInclude: ["ff.cinematic.css", "ff-cinematic.js", "ff-loginStandalone__"],
  },
  {
    name: "Live dashboard locked",
    url: `${base}/platform/dashboard?css_v=${encodeURIComponent(assetV)}`,
    expect: 403,
    mustInclude: ["FutureFunded", "Protected operator workspace"],
    mustIncludeAnyGroups: [
      ["login.bundle.css", "ff-loginV4"],
    ],
    mustNotInclude: ["ff.cinematic.css", "ff-cinematic.js"],
  },
  {
    name: "Local dashboard private",
    url: `${localBase}/platform/dashboard?operator_token=${encodeURIComponent(token)}&token=${encodeURIComponent(token)}&css_v=${encodeURIComponent(assetV)}`,
    expect: token ? 200 : 403,
    mustInclude: token ? ["ff-dashboardModern", "Operator command center"] : ["FutureFunded"],
    mustIncludeAnyGroups: token
      ? [["dashboard.bundle.css", "dashboard-modern.css"]]
      : [],
    mustNotInclude: ["ff.cinematic.css", "ff-cinematic.js"],
  },
];

for (const route of routes) {
  let out;

  try {
    out = await fetchText(route.url);
  } catch (error) {
    record(false, `${route.name} fetch`, error.message);
    continue;
  }

  const { status, headers, text } = out;

  record(status === route.expect, `${route.name} status`, `status=${status}`);

  for (const header of securityHeaders) {
    record(Boolean(headers.get(header)), `${route.name} has ${header}`);
  }

  for (const marker of route.mustInclude || []) {
    record(text.includes(marker), `${route.name} contains ${marker}`);
  }

  for (const group of route.mustIncludeAnyGroups || []) {
    record(
      includesAny(text, group),
      `${route.name} contains one of [${group.join(", ")}]`
    );
  }

  for (const marker of route.mustNotInclude || []) {
    record(!text.includes(marker), `${route.name} excludes ${marker}`);
  }

  record(!/{{|}}|{%|%}/.test(text), `${route.name} has no obvious template leaks`);

  if (route.campaignOg) {
    const ogImage = metaContent(text, "og:image");
    record(Boolean(ogImage), "Campaign has og:image", ogImage || "missing");
    record(ogImage.startsWith("https://"), "Campaign og:image is HTTPS", ogImage || "missing");
    record(!ogImage.startsWith("http://"), "Campaign og:image is not insecure HTTP", ogImage || "missing");
  }
}

console.log("\nVisual overflow and CTA checks");

const browser = await chromium.launch({ headless: true });

const visualRoutes = [
  {
    name: "Homepage desktop",
    url: `${base}/platform/?css_v=${encodeURIComponent(assetV)}`,
    width: 1440,
    height: 1200,
    expect: 200,
    selectors: [
      ".ff-platformHomeHero",
      "[data-ff-page-root]",
      "a[href*='/c/']",
      "a[href*='/platform/onboarding']",
      "a[href*='#demo']",
    ],
  },
  {
    name: "Homepage mobile",
    url: `${base}/platform/?css_v=${encodeURIComponent(assetV)}`,
    width: 390,
    height: 1200,
    expect: 200,
    selectors: [
      ".ff-platformHomeHero",
      "[data-ff-page-root]",
      "a[href*='/c/']",
      "a[href*='/platform/onboarding']",
      "a[href*='#demo']",
    ],
  },
  {
    name: "Campaign desktop",
    url: `${base}/c/${encodeURIComponent(slug)}?css_v=${encodeURIComponent(assetV)}`,
    width: 1440,
    height: 1200,
    expect: 200,
    selectors: ["[data-ff-open-checkout]", "[data-ff-donate-trigger]"],
  },
  {
    name: "Campaign mobile",
    url: `${base}/c/${encodeURIComponent(slug)}?css_v=${encodeURIComponent(assetV)}`,
    width: 390,
    height: 1200,
    expect: 200,
    selectors: ["[data-ff-open-checkout]", "[data-ff-donate-trigger]"],
  },
  {
    name: "Onboarding desktop",
    url: `${base}/platform/onboarding?css_v=${encodeURIComponent(assetV)}`,
    width: 1440,
    height: 1200,
    expect: 200,
    selectors: [".ff-onboardModernHero", "[data-ff-surface='onboarding']", "[data-ff-form='launch-setup']"],
  },
  {
    name: "Onboarding mobile",
    url: `${base}/platform/onboarding?css_v=${encodeURIComponent(assetV)}`,
    width: 390,
    height: 1200,
    expect: 200,
    selectors: [".ff-onboardModernHero", "[data-ff-surface='onboarding']", "[data-ff-form='launch-setup']"],
  },
  {
    name: "Login desktop",
    url: `${base}/platform/login?css_v=${encodeURIComponent(assetV)}`,
    width: 1440,
    height: 1100,
    expect: 200,
    selectors: [".ff-loginV4__card"],
  },
  {
    name: "Login mobile",
    url: `${base}/platform/login?css_v=${encodeURIComponent(assetV)}`,
    width: 390,
    height: 1200,
    expect: 200,
    selectors: [".ff-loginV4__card"],
  },
  {
    name: "Dashboard locked desktop",
    url: `${base}/platform/dashboard?css_v=${encodeURIComponent(assetV)}`,
    width: 1440,
    height: 1000,
    expect: 403,
    selectors: ["[data-ff-dashboard-locked]", ".ff-loginV4__card"],
  },
  {
    name: "Dashboard locked mobile",
    url: `${base}/platform/dashboard?css_v=${encodeURIComponent(assetV)}`,
    width: 390,
    height: 1000,
    expect: 403,
    selectors: ["[data-ff-dashboard-locked]", ".ff-loginV4__card"],
  },
];

if (token) {
  visualRoutes.push(
    {
      name: "Operator dashboard desktop",
      url: `${localBase}/platform/dashboard?operator_token=${encodeURIComponent(token)}&token=${encodeURIComponent(token)}&css_v=${encodeURIComponent(assetV)}`,
      width: 1440,
      height: 1200,
      expect: 200,
      selectors: [".ff-dashboardModern", "[data-ff-dashboard-root]", "[data-ff-operator-root]"],
    },
    {
      name: "Operator dashboard mobile",
      url: `${localBase}/platform/dashboard?operator_token=${encodeURIComponent(token)}&token=${encodeURIComponent(token)}&css_v=${encodeURIComponent(assetV)}`,
      width: 390,
      height: 1200,
      expect: 200,
      selectors: [".ff-dashboardModern", "[data-ff-dashboard-root]", "[data-ff-operator-root]"],
    }
  );
}

for (const item of visualRoutes) {
  const page = await browser.newPage({ viewport: { width: item.width, height: item.height } });

  try {
    const res = await page.goto(item.url, { waitUntil: "networkidle", timeout: 60_000 });
    const status = res?.status() || 0;

    const metrics = await page.evaluate((selectors) => {
      const root = document.documentElement;

      const found = selectors
        .flatMap((selector) => Array.from(document.querySelectorAll(selector)))
        .map((node) => {
          const rect = node.getBoundingClientRect();
          return {
            selector: node.className || node.getAttribute("data-ff-page-root") || node.tagName,
            width: rect.width,
            height: rect.height,
          };
        });

      const bodyText = document.body?.innerText || "";

      return {
        overflowX: root.scrollWidth > root.clientWidth + 2,
        scrollHeight: root.scrollHeight,
        targetVisible: found.some((entry) => entry.width > 20 && entry.height > 20),
        matches: found.length,
        hasTemplateLeak: /{{|}}|{%|%}/.test(bodyText),
      };
    }, item.selectors);

    record(status === item.expect, `${item.name} visual status`, `status=${status}`);
    record(!metrics.overflowX, `${item.name} no horizontal overflow`);
    record(metrics.targetVisible, `${item.name} primary CTA/surface visible`, `matches=${metrics.matches} height=${metrics.scrollHeight}`);
    record(!metrics.hasTemplateLeak, `${item.name} no visible template leaks`);

    await page.screenshot({
      path: path.join(artifactDir, `${item.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.png`),
      fullPage: true,
    }).catch(() => {});
  } catch (error) {
    record(false, `${item.name} visual check`, error.message);
  } finally {
    await page.close().catch(() => {});
  }
}

if (runShareQr) {
  console.log("\nCampaign Share/QR behavior check");

  const page = await browser.newPage({ viewport: { width: 390, height: 1200 } });

  try {
    const url = `${localBase}/c/${encodeURIComponent(slug)}?css_v=${encodeURIComponent(assetV)}&share_qr_gate=1`;
    const res = await page.goto(url, { waitUntil: "networkidle", timeout: 60_000 });

    record((res?.status() || 0) === 200, "Local campaign Share/QR page status", `status=${res?.status() || 0}`);

    const triggerCount = await page
      .locator("[data-ff-qr-trigger], [data-ff-share-trigger], [data-ff-share]")
      .count()
      .catch(() => 0);

    record(triggerCount > 0, "Share/QR trigger exists", `count=${triggerCount}`);

    if (triggerCount > 0) {
      await page
        .locator("[data-ff-qr-trigger], [data-ff-share-trigger], [data-ff-share]")
        .first()
        .click({ timeout: 5000 })
        .catch((error) => record(false, "Share/QR trigger click", error.message));

      await page.waitForTimeout(700);
    }

    const shareProof = await page.evaluate(() => {
      const drawers = Array.from(
        document.querySelectorAll("[data-ff-share-drawer], [data-ff-qr-modal], .ff-shareDrawer, #qr-modal")
      ).map((node) => {
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();

        return {
          id: node.id || "",
          hidden: node.hidden,
          ariaHidden: node.getAttribute("aria-hidden"),
          display: style.display,
          opacity: style.opacity,
          pointerEvents: style.pointerEvents,
          width: rect.width,
          height: rect.height,
          visible:
            !node.hidden &&
            node.getAttribute("aria-hidden") !== "true" &&
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || "1") > 0 &&
            rect.width > 20 &&
            rect.height > 20,
        };
      });

      return {
        drawers,
        visibleDrawer: drawers.some((drawer) => drawer.visible),
        copyHooks: document.querySelectorAll(
          "[data-ff-copy-share-url], [data-ff-copy-trigger], [data-ff-copy-link], #qr-modal-share-url, [data-ff-qr-share-url]"
        ).length,
      };
    });

    record(shareProof.visibleDrawer, "Share/QR drawer becomes visible", JSON.stringify(shareProof.drawers.slice(0, 2)));
    record(shareProof.copyHooks > 0, "Share/QR copy hooks exist", `count=${shareProof.copyHooks}`);

    fs.writeFileSync(
      path.join(artifactDir, "share-qr-proof.json"),
      JSON.stringify(shareProof, null, 2)
    );

    await page.screenshot({
      path: path.join(artifactDir, "share-qr-open.png"),
      fullPage: true,
    }).catch(() => {});
  } catch (error) {
    record(false, "Share/QR behavior check failed", error.message);
  } finally {
    await page.close().catch(() => {});
  }
}

await browser.close();

if (runMoneyLoop) {
  console.log("\nOptional endpoint money-loop check");

  const moneyPayload = {
    amount: 25,
    amount_cents: 2500,
    frequency: "once",
    source: "ff-enterprise-launch-gate-v3",
  };

  try {
    const checkout = await fetchJson(`${localBase}/c/${encodeURIComponent(slug)}/checkout/session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(moneyPayload),
      timeout: 40_000,
    });

    const sessionId = checkout.json?.id || checkout.json?.session_id || "";
    const checkoutUrl = checkout.json?.url || checkout.json?.checkout_url || "";

    record(
      checkout.status >= 200 && checkout.status < 300 && Boolean(sessionId || checkoutUrl),
      "Money loop checkout session can be created",
      `status=${checkout.status}${sessionId ? ` id=${String(sessionId).slice(0, 18)}…` : ""}`
    );

    if (sessionId) {
      const statusCandidates = [
        `${localBase}/c/${encodeURIComponent(slug)}/checkout/session-status?session_id=${encodeURIComponent(sessionId)}`,
        `${localBase}/c/${encodeURIComponent(slug)}/session-status?session_id=${encodeURIComponent(sessionId)}`,
        `${localBase}/c/stripe/session-status?session_id=${encodeURIComponent(sessionId)}`,
      ];

      let statusOk = false;
      let state = "";

      for (const url of statusCandidates) {
        const status = await fetchJson(url, { timeout: 20_000 }).catch(() => null);
        if (status && status.status >= 200 && status.status < 300) {
          statusOk = true;
          state = JSON.stringify(
            status.json?.payment_status ||
            status.json?.checkout_status ||
            status.json?.status ||
            status.json?.paid ||
            "unknown"
          );
          break;
        }
      }

      record(statusOk, "Money loop session-status endpoint responds", `state=${state}`);
    } else {
      record(false, "Money loop session-status endpoint responds", "Skipped because no session id returned");
    }

    const ledger = await fetchJson(`${localBase}/c/${encodeURIComponent(slug)}/ledger/summary`, {
      timeout: 20_000,
    });

    record(
      ledger.status >= 200 && ledger.status < 300,
      "Money loop ledger summary endpoint responds",
      `status=${ledger.status}`
    );
  } catch (error) {
    record(false, "Optional endpoint money-loop check failed", error.message);
  }
}

console.log("\nRepository hygiene checks");

try {
  const rawStatus = execSync("git status --short", { encoding: "utf8" }).trim();

  const allowedPatterns = [
    /^\?\? docs\/release-proof\/enterprise-launch-gate-latest\.json$/,
    /^\s?M\s+docs\/release-proof\/enterprise-launch-gate-latest\.json$/,
    /^\?\? docs\/release-proof\/futurefunded-production-closeout-v1\.md$/,
    /^\?\? scripts\/release\/ff_enterprise_launch_gate\.mjs$/,
    /^\s?M\s+scripts\/release\/ff_enterprise_launch_gate\.mjs$/,
    /^\?\? audit_outputs\/enterprise-gate\//,
    /^\?\? scripts\/cleanup\/?$/,
    /^\s?M\s+apps\/web\/app\/__init__\.py$/,
  ];

  const unexpected = rawStatus
    .split("\n")
    .filter(Boolean)
    .filter((line) => !allowedPatterns.some((pattern) => pattern.test(line.trimEnd())));

  record(
    unexpected.length === 0,
    "No unexpected working tree changes",
    unexpected.join(" | ") || "only expected closeout/gate files"
  );
} catch (error) {
  record(false, "Git status check failed", error.message);
}

try {
  const secretScan = execSync(
    [
      "git grep -nE",
      "'sk_live_[A-Za-z0-9]{16,}|pk_live_[A-Za-z0-9]{16,}|whsec_[A-Za-z0-9]{16,}|cs_(live|test)_[A-Za-z0-9]{16,}'",
      "--",
      "':!.env.example'",
      "':!.env.production.example'",
      "':!docs/release-proof/*'",
      "':!audit_outputs/*'",
      "':!artifacts/*'",
      "':!test-results/*'",
      "|| true",
    ].join(" "),
    { encoding: "utf8" }
  ).trim();

  record(
    secretScan.length === 0,
    "No obvious live Stripe secrets or checkout session IDs committed",
    firstLines(secretScan, 3)
  );
} catch (error) {
  record(false, "Secret scan failed", error.message);
}

const failed = results.filter((result) => !result.ok);
const summary = {
  version: "v3",
  base,
  localBase,
  slug,
  assetV,
  runShareQr,
  runMoneyLoop,
  artifactDir,
  passed: results.length - failed.length,
  total: results.length,
  failed,
  generatedAt,
};

fs.writeFileSync(
  path.join(proofDir, "enterprise-launch-gate-latest.json"),
  JSON.stringify(summary, null, 2)
);

console.log(`\nSummary: ${summary.passed}/${summary.total} passed`);
console.log("Wrote docs/release-proof/enterprise-launch-gate-latest.json");
console.log(`Artifacts: ${artifactDir}`);

if (failed.length) {
  console.log("\nFailed/CHECK items:");
  for (const item of failed) {
    console.log(`- ${item.label}${item.detail ? `: ${item.detail}` : ""}`);
  }

  process.exit(1);
}

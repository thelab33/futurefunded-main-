#!/usr/bin/env node
import fs from "node:fs/promises";
import fss from "node:fs";
import path from "node:path";

let playwright;
try {
  playwright = await import("@playwright/test");
} catch {
  playwright = await import("playwright");
}

const { chromium } = playwright;

const ROOT = process.cwd();
const BASE_URL = (process.env.FF_BASE_URL || "https://getfuturefunded.com").replace(/\/+$/, "");
const OUT_ROOT = path.join(ROOT, "audit_outputs", "hoi-6c-copy");
const STAMP = new Date().toISOString().replace(/[:.]/g, "-");
const RUN_DIR = path.join(OUT_ROOT, STAMP);
const LATEST_DIR = path.join(OUT_ROOT, "latest");
const VISUAL_LATEST = path.join(ROOT, "audit_outputs", "visual-launch", "latest");

const PAGES = [
  {
    key: "platform",
    label: "Platform homepage",
    path: "/platform/",
    goal: "Enterprise SaaS clarity: one premium product, one confident promise.",
  },
  {
    key: "campaign",
    label: "Campaign page",
    path: "/c/connect-atx-elite",
    goal: "Donor confidence: one clear reason to give, one dominant action.",
  },
  {
    key: "login",
    label: "Login",
    path: "/platform/login",
    goal: "Secure operator access with calm trust language.",
  },
  {
    key: "onboarding",
    label: "Onboarding",
    path: "/platform/onboarding",
    goal: "Make new teams feel guided and close to launch.",
  },
  {
    key: "dashboard_locked",
    label: "Dashboard locked",
    path: "/platform/dashboard",
    goal: "Protected operator surface, not a broken error page.",
    protected: true,
  },
];

const VIEWPORTS = [
  { key: "mobile", width: 390, height: 844 },
  { key: "desktop", width: 1440, height: 1100 },
];

function urlFor(pagePath) {
  return new URL(pagePath, `${BASE_URL}/`).toString();
}

function clean(value = "") {
  return String(value).replace(/\s+/g, " ").trim();
}

function gradeFor(score) {
  if (score >= 92) return "A";
  if (score >= 84) return "B";
  if (score >= 74) return "C";
  if (score >= 64) return "D";
  return "F";
}

function wordCount(text = "") {
  return clean(text).split(/\s+/).filter(Boolean).length;
}

function sentenceCount(text = "") {
  return clean(text).split(/[.!?]+/).filter(Boolean).length;
}

function scoreItem(item) {
  let score = 100;

  score -= item.longHeadings.length * 7;
  score -= item.denseParagraphs.length * 5;
  score -= item.wordyButtons.length * 4;
  score -= item.weakCtas.length * 8;
  score -= item.heroWordCount > 42 ? 8 : 0;
  score -= item.totalCtas > 18 && item.viewport === "mobile" ? 6 : 0;
  score -= item.totalWords > 1700 && item.viewport === "mobile" ? 5 : 0;
  score -= item.hasJinjaLeak ? 25 : 0;
  score -= item.hasPlaceholderCopy ? 25 : 0;

  return Math.max(0, score);
}

function copyRecommendation(text, kind) {
  const t = clean(text);

  if (kind === "heading") {
    if (/fuel|fund|future|season/i.test(t)) return "Keep the promise punchy. Ideal: “Fuel the season. Fund the future.”";
    if (t.length > 92) return "Compress to one decisive line under 72 characters.";
    return "Good. Keep balanced and concrete.";
  }

  if (kind === "paragraph") {
    if (wordCount(t) > 44) return "Split into 1–2 shorter lines. Lead with outcome, then trust proof.";
    if (sentenceCount(t) > 2) return "Cut to two sentences max for mobile.";
    return "Good. Keep it donor-first.";
  }

  if (kind === "button") {
    if (wordCount(t) > 4) return "Shorten CTA to 2–4 words.";
    if (/learn more/i.test(t)) return "Use a higher-intent CTA if this is above the fold.";
    return "Good. Keep one primary CTA visually dominant.";
  }

  return "Review for clarity, trust, and mobile scan speed.";
}

async function ensureDirs() {
  await fs.mkdir(RUN_DIR, { recursive: true });
}

async function copyLatest() {
  await fs.rm(LATEST_DIR, { recursive: true, force: true });
  await fs.cp(RUN_DIR, LATEST_DIR, { recursive: true });
}

async function auditPage(browser, pageDef, viewport) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: 1,
    colorScheme: "light",
    reducedMotion: "reduce",
  });

  const page = await context.newPage();
  const consoleErrors = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(clean(msg.text()));
  });

  const url = urlFor(pageDef.path);
  let status = null;
  let navError = null;

  try {
    const response = await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 45000,
    });

    status = response?.status() ?? null;
    await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
    await page.evaluate(() => document.fonts?.ready).catch(() => {});
    await page.waitForTimeout(350);
  } catch (error) {
    navError = error.message;
  }

  const dom = await page.evaluate(() => {
    const visible = (el) => {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };

    const textOf = (el) =>
      [
        el.innerText,
        el.getAttribute("aria-label"),
        el.getAttribute("title"),
        el.getAttribute("value"),
      ]
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();

    const headings = [...document.querySelectorAll("h1,h2,h3")]
      .filter(visible)
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        text: textOf(el),
        chars: textOf(el).length,
      }))
      .filter((x) => x.text)
      .slice(0, 80);

    const paragraphs = [...document.querySelectorAll("p,li")]
      .filter(visible)
      .map((el) => ({
        text: textOf(el),
        chars: textOf(el).length,
        words: textOf(el).split(/\s+/).filter(Boolean).length,
      }))
      .filter((x) => x.text)
      .slice(0, 220);

    const buttons = [
      ...document.querySelectorAll("a,button,[role='button'],input[type='submit'],input[type='button']"),
    ]
      .filter(visible)
      .map((el) => ({
        text: textOf(el),
        href: el.getAttribute("href") || "",
        hooks: [...el.attributes]
          .filter((a) => a.name.startsWith("data-ff"))
          .map((a) => a.name),
      }))
      .filter((x) => x.text)
      .slice(0, 160);

    const hero = document.querySelector("main, header, section") || document.body;
    const heroText = textOf(hero).slice(0, 900);

    return {
      title: document.title || "",
      bodyText: document.body?.innerText?.replace(/\s+/g, " ").trim() || "",
      headings,
      paragraphs,
      buttons,
      heroText,
      viewportWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
    };
  }).catch((error) => ({
    evalError: error.message,
    title: "",
    bodyText: "",
    headings: [],
    paragraphs: [],
    buttons: [],
    heroText: "",
    viewportWidth: viewport.width,
    scrollWidth: viewport.width,
  }));

  await context.close();

  const longHeadings = dom.headings
    .filter((h) => (h.tag === "h1" && h.chars > 78) || (h.tag !== "h1" && h.chars > 96))
    .map((h) => ({ ...h, recommendation: copyRecommendation(h.text, "heading") }));

  const denseParagraphs = dom.paragraphs
    .filter((p) => p.words > 42 || p.chars > 260)
    .map((p) => ({ ...p, recommendation: copyRecommendation(p.text, "paragraph") }))
    .slice(0, 12);

  const wordyButtons = dom.buttons
    .filter((b) => wordCount(b.text) > 5)
    .map((b) => ({ ...b, recommendation: copyRecommendation(b.text, "button") }))
    .slice(0, 12);

  const weakCtas = dom.buttons
    .filter((b) => /learn more|click here|submit|continue$/i.test(b.text))
    .map((b) => ({ ...b, recommendation: "Use a more specific outcome-driven CTA." }))
    .slice(0, 12);

  const hasJinjaLeak = /\{\{.*?\}\}|\{%.*?%\}/.test(dom.bodyText);
  const hasPlaceholderCopy = /\blorem\b|\bipsum\b|\btodo\b|\btbd\b|\bplaceholder\b|\bdemo only\b/i.test(dom.bodyText);

  const result = {
    pageKey: pageDef.key,
    label: pageDef.label,
    goal: pageDef.goal,
    viewport: viewport.key,
    url,
    status,
    navError,
    consoleErrors,
    title: dom.title,
    heroWordCount: wordCount(dom.heroText),
    totalWords: wordCount(dom.bodyText),
    totalHeadings: dom.headings.length,
    totalParagraphs: dom.paragraphs.length,
    totalCtas: dom.buttons.length,
    scrollWidth: dom.scrollWidth,
    viewportWidth: dom.viewportWidth,
    longHeadings,
    denseParagraphs,
    wordyButtons,
    weakCtas,
    hasJinjaLeak,
    hasPlaceholderCopy,
  };

  result.score = scoreItem(result);
  result.grade = gradeFor(result.score);

  return result;
}

function buildMarkdown(report) {
  const lines = [
    "# FutureFunded HOI 6C — Production Screenshot + Copy Review",
    "",
    `**Status:** ${report.ok ? "PASS ✅" : "REVIEW ⚠️"}`,
    `**Base URL:** ${report.baseUrl}`,
    `**Checked:** ${report.checkedAt}`,
    `**Average score:** ${report.averageScore}/100 (${gradeFor(report.averageScore)})`,
    "",
    "## Why this exists",
    "",
    "This report turns production pages and latest visual screenshots into a surgical frontend brief: shorter copy, cleaner CTAs, calmer density, stronger mobile fold clarity, and more unified typography.",
    "",
    "## Production screenshot folder",
    "",
    `\`${report.visualScreenshotsPath}\``,
    "",
    "## Page summary",
    "",
    "| Page | Viewport | Score | Words | CTAs | Long headings | Dense copy | Wordy buttons |",
    "|---|---:|---:|---:|---:|---:|---:|---:|",
    ...report.results.map(
      (r) =>
        `| ${r.label} | ${r.viewport} | ${r.score} ${r.grade} | ${r.totalWords} | ${r.totalCtas} | ${r.longHeadings.length} | ${r.denseParagraphs.length} | ${r.wordyButtons.length} |`
    ),
    "",
    "## Surgical priorities",
    "",
  ];

  const priorityRows = report.results
    .filter(
      (r) =>
        r.longHeadings.length ||
        r.denseParagraphs.length ||
        r.wordyButtons.length ||
        r.weakCtas.length ||
        r.hasJinjaLeak ||
        r.hasPlaceholderCopy
    )
    .sort((a, b) => a.score - b.score);

  if (!priorityRows.length) {
    lines.push("- ✅ No major copy compression issues found. Move to visual screenshot review and final human taste pass.");
  } else {
    for (const r of priorityRows) {
      lines.push(`### ${r.label} / ${r.viewport}`);
      lines.push("");
      lines.push(`Goal: ${r.goal}`);
      lines.push("");
      if (r.longHeadings.length) {
        lines.push("**Long headings**");
        for (const h of r.longHeadings.slice(0, 5)) {
          lines.push(`- ${h.tag.toUpperCase()}: “${h.text}”`);
          lines.push(`  - ${h.recommendation}`);
        }
        lines.push("");
      }

      if (r.denseParagraphs.length) {
        lines.push("**Dense copy blocks**");
        for (const p of r.denseParagraphs.slice(0, 5)) {
          lines.push(`- “${p.text.slice(0, 220)}${p.text.length > 220 ? "…" : ""}”`);
          lines.push(`  - ${p.recommendation}`);
        }
        lines.push("");
      }

      if (r.wordyButtons.length) {
        lines.push("**Wordy CTAs**");
        for (const b of r.wordyButtons.slice(0, 6)) {
          lines.push(`- “${b.text}”`);
          lines.push(`  - ${b.recommendation}`);
        }
        lines.push("");
      }

      if (r.weakCtas.length) {
        lines.push("**Weak CTAs**");
        for (const b of r.weakCtas.slice(0, 6)) {
          lines.push(`- “${b.text}”`);
          lines.push(`  - ${b.recommendation}`);
        }
        lines.push("");
      }
    }
  }

  lines.push(
    "",
    "## Recommended launch copy system",
    "",
    "| Surface | Preferred copy pattern |",
    "|---|---|",
    "| Campaign hero | Outcome first. One sentence max. One dominant donate CTA. |",
    "| Donation panel | “Choose an amount. Secure checkout. Every gift helps.” |",
    "| Sponsor CTA | “Become a sponsor” / “Sponsor the season.” |",
    "| Share CTA | “Share campaign” / “Copy link.” |",
    "| Platform hero | “Launch trusted fundraising pages for teams, schools, and clubs.” |",
    "| Login | “Sign in to manage campaigns, sponsors, and donations.” |",
    "| Onboarding | “Set up your campaign in minutes.” |",
    "| Locked dashboard | “Operator access required.” Not “Forbidden.” |",
    "",
    "## Next patch guidance",
    "",
    "1. Keep the campaign hero emotional but short.",
    "2. Make donate visually dominant on mobile.",
    "3. Reduce secondary CTAs to quieter pills or text links.",
    "4. Keep body copy under two sentences per block.",
    "5. Make protected dashboard states feel intentional, secure, and branded.",
    ""
  );

  return lines.join("\n");
}

await ensureDirs();

const browser = await chromium.launch({ headless: true });
const results = [];

for (const pageDef of PAGES) {
  for (const viewport of VIEWPORTS) {
    console.log(`Reviewing ${pageDef.label} / ${viewport.key}`);
    results.push(await auditPage(browser, pageDef, viewport));
  }
}

await browser.close();

const averageScore = Math.round(results.reduce((sum, r) => sum + r.score, 0) / Math.max(results.length, 1));
const report = {
  ok: averageScore >= 90 && results.every((r) => !r.hasJinjaLeak && !r.hasPlaceholderCopy),
  checkedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  visualScreenshotsPath: path.join(VISUAL_LATEST, "screenshots"),
  averageScore,
  results,
};

await fs.writeFile(path.join(RUN_DIR, "report.json"), JSON.stringify(report, null, 2) + "\n", "utf8");
await fs.writeFile(path.join(RUN_DIR, "report.md"), buildMarkdown(report), "utf8");

await fs.rm(LATEST_DIR, { recursive: true, force: true });
await fs.cp(RUN_DIR, LATEST_DIR, { recursive: true });

console.log("");
console.log(fss.readFileSync(path.join(LATEST_DIR, "report.md"), "utf8"));
console.log("");
console.log(`HOI 6C report: ${path.join(LATEST_DIR, "report.md")}`);

process.exit(report.ok ? 0 : 1);

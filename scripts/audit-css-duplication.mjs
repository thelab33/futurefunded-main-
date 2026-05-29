import fs from "node:fs/promises";
import path from "node:path";

const files = {
  core: "apps/web/app/static/css/ff.css",
  homepage: "apps/web/app/static/css/ff.homepage-flagship.css",
  campaignPolish: "apps/web/app/static/css/ff.campaign-polish.css",
  legacyMicropolish: "apps/web/app/static/css/ff.ui-micropolish.css",
};

const templates = {
  homepage: "apps/web/app/templates/platform/index.html",
  campaign: "apps/web/app/templates/campaign/index.html",
};

const primitiveNeedles = [
  ".ff-button",
  ".ff-btn",
  ".ff-card",
  ".ff-shell",
  ".ff-container",
  ".ff-h1",
  ".ff-h2",
  ".ff-h3",
  ".ff-h4",
  ".ff-section",
  ".ff-site-header",
  ".ff-site-header__bar",
  ".ff-brand-lockup",
  ".ff-logo",
  ".ff-header-actions",
  ".ff-primary-nav",
  ".ff-site-nav",
  ".ff-kicker",
  ".ff-tag",
  ".ff-progress",
  ".ff-progress__track",
  ".ff-progress__bar",
  ".ff-stat",
  ".ff-lede",
  ".ff-copy",
  ".ff-micro",
];

const allowedHomepagePrefixes = [
  ".ff-platformPremium",
  'html[data-theme="dark"] .ff-platformPremium',
  'html[data-ff-theme="dark"] .ff-platformPremium',
  "@media",
  "@supports",
];

function stripComments(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

function normalizeWhitespace(value) {
  return value.replace(/\s+/g, " ").trim();
}

function splitSelectorList(selectorText) {
  const selectors = [];
  let current = "";
  let depth = 0;
  let quote = "";

  for (const char of selectorText) {
    if (quote) {
      current += char;
      if (char === quote) quote = "";
      continue;
    }

    if (char === '"' || char === "'") {
      quote = char;
      current += char;
      continue;
    }

    if (char === "(" || char === "[") {
      depth += 1;
      current += char;
      continue;
    }

    if (char === ")" || char === "]") {
      depth = Math.max(0, depth - 1);
      current += char;
      continue;
    }

    if (char === "," && depth === 0) {
      const selector = normalizeWhitespace(current);
      if (selector) selectors.push(selector);
      current = "";
      continue;
    }

    current += char;
  }

  const tail = normalizeWhitespace(current);
  if (tail) selectors.push(tail);

  return selectors;
}

function parseDeclarations(body) {
  return body
    .split(";")
    .map((decl) => decl.trim())
    .filter(Boolean)
    .map((decl) => {
      const idx = decl.indexOf(":");
      if (idx === -1) return null;

      const prop = normalizeWhitespace(decl.slice(0, idx)).toLowerCase();
      const value = normalizeWhitespace(decl.slice(idx + 1));

      return { prop, value, fingerprint: `${prop}: ${value}` };
    })
    .filter(Boolean);
}

function parseCssRules(css, fileKey) {
  const clean = stripComments(css);
  const rules = [];
  const regex = /([^{}]+)\{([^{}]*)\}/g;
  let match;

  while ((match = regex.exec(clean))) {
    const rawSelector = normalizeWhitespace(match[1]);
    const body = match[2];

    if (!rawSelector || rawSelector.startsWith("@keyframes")) continue;
    if (rawSelector.includes("from") || rawSelector.includes("to")) continue;

    const selectors = splitSelectorList(rawSelector);
    const declarations = parseDeclarations(body);

    for (const selector of selectors) {
      rules.push({
        fileKey,
        selector,
        declarations,
        declarationFingerprints: declarations.map((d) => d.fingerprint),
      });
    }
  }

  return rules;
}

function parseVars(css, fileKey) {
  const matches = [...css.matchAll(/(--ff-[A-Za-z0-9_-]+)\s*:\s*([^;]+);/g)];
  return matches.map((match) => ({
    fileKey,
    name: match[1],
    value: normalizeWhitespace(match[2]),
    references: [...match[2].matchAll(/var\((--ff-[A-Za-z0-9_-]+)/g)].map((m) => m[1]),
  }));
}

async function readMaybe(filePath) {
  try {
    return await fs.readFile(filePath, "utf8");
  } catch {
    return "";
  }
}

function groupBy(items, keyFn) {
  const map = new Map();

  for (const item of items) {
    const key = keyFn(item);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(item);
  }

  return [...map.entries()];
}

function unique(values) {
  return [...new Set(values)];
}

function isHomepageSelectorUnsafe(selector) {
  if (!selector.includes(".ff-")) return false;

  const touchesPrimitive = primitiveNeedles.some((needle) => selector.includes(needle));
  if (!touchesPrimitive) return false;

  const isScoped = selector.includes(".ff-platformPremium");
  return !isScoped;
}

function isHomepageScopedPrimitiveOverride(selector) {
  return (
    selector.includes(".ff-platformPremium") &&
    primitiveNeedles.some((needle) => selector.includes(needle))
  );
}

function isMicropolishPrimitiveOverride(selector) {
  return primitiveNeedles.some((needle) => selector.includes(needle));
}

const cssTexts = {};
for (const [key, filePath] of Object.entries(files)) {
  cssTexts[key] = await readMaybe(filePath);
}

const templateTexts = {};
for (const [key, filePath] of Object.entries(templates)) {
  templateTexts[key] = await readMaybe(filePath);
}

const allRules = Object.entries(cssTexts).flatMap(([key, css]) => parseCssRules(css, key));

const allVars = Object.entries(cssTexts).flatMap(([key, css]) => parseVars(css, key));

const selectorGroups = groupBy(allRules, (rule) => rule.selector)
  .map(([selector, rules]) => ({
    selector,
    files: unique(rules.map((rule) => rule.fileKey)),
    count: rules.length,
  }))
  .filter((group) => group.files.length > 1)
  .sort((a, b) => b.files.length - a.files.length || a.selector.localeCompare(b.selector));

const declarationGroups = groupBy(
  allRules.flatMap((rule) =>
    rule.declarations.map((decl) => ({
      fileKey: rule.fileKey,
      selector: rule.selector,
      fingerprint: decl.fingerprint,
    }))
  ),
  (entry) => entry.fingerprint
)
  .map(([fingerprint, entries]) => ({
    fingerprint,
    files: unique(entries.map((entry) => entry.fileKey)),
    selectors: unique(entries.map((entry) => entry.selector)).slice(0, 24),
    count: entries.length,
  }))
  .filter((group) => group.files.length > 1 && group.count >= 3)
  .sort((a, b) => b.count - a.count)
  .slice(0, 80);

const varGroups = groupBy(allVars, (entry) => entry.name)
  .map(([name, entries]) => ({
    name,
    files: unique(entries.map((entry) => entry.fileKey)),
    values: unique(entries.map((entry) => entry.value)),
    references: unique(entries.flatMap((entry) => entry.references)),
  }))
  .filter((group) => group.files.length > 1 || group.references.length)
  .sort((a, b) => a.name.localeCompare(b.name));

const homepageUnsafeGlobals = allRules
  .filter((rule) => rule.fileKey === "homepage")
  .filter((rule) => isHomepageSelectorUnsafe(rule.selector))
  .map((rule) => rule.selector);

const homepageScopedPrimitiveOverrides = allRules
  .filter((rule) => rule.fileKey === "homepage")
  .filter((rule) => isHomepageScopedPrimitiveOverride(rule.selector))
  .map((rule) => rule.selector);

const campaignPolishPrimitiveOverrides = allRules
  .filter((rule) => rule.fileKey === "campaignPolish")
  .filter((rule) => isMicropolishPrimitiveOverride(rule.selector))
  .map((rule) => rule.selector);

const loadOrder = {
  homepage: {
    loadsCore: templateTexts.homepage.includes("css/ff.css"),
    loadsHomepage: templateTexts.homepage.includes("css/ff.homepage-flagship.css"),
    loadsCampaignPolish: templateTexts.homepage.includes("css/ff.campaign-polish.css"),
  },
  campaign: {
    loadsCore: templateTexts.campaign.includes("css/ff.css"),
    loadsHomepage: templateTexts.campaign.includes("css/ff.homepage-flagship.css"),
    loadsCampaignPolish: templateTexts.campaign.includes("css/ff.campaign-polish.css"),
  },
};

const recommendations = [];

if (homepageScopedPrimitiveOverrides.length) {
  recommendations.push(
    "Homepage CSS is scoped, but it still overrides shared primitives. Review these and keep only layout-specific composition."
  );
}

if (campaignPolishPrimitiveOverrides.length) {
  recommendations.push(
    "ff.campaign-polish.css currently overrides many shared primitives. Treat it as campaign authority, or migrate reusable primitive rules back into ff.css."
  );
}

if (loadOrder.homepage.loadsCore && loadOrder.homepage.loadsHomepage) {
  recommendations.push(
    "Homepage load order is correct: ff.css foundation first, homepage composition second."
  );
}

if (loadOrder.campaign.loadsCore && loadOrder.campaign.loadsCampaignPolish) {
  recommendations.push(
    "Campaign load order is correct, but ff.campaign-polish.css should be treated as campaign-specific until cleaned."
  );
}

const result = {
  ok: homepageUnsafeGlobals.length === 0,
  files,
  loadOrder,
  counts: {
    rules: Object.fromEntries(
      Object.keys(files).map((key) => [key, allRules.filter((rule) => rule.fileKey === key).length])
    ),
    vars: Object.fromEntries(
      Object.keys(files).map((key) => [
        key,
        allVars.filter((entry) => entry.fileKey === key).length,
      ])
    ),
    overlappingSelectors: selectorGroups.length,
    repeatedDeclarations: declarationGroups.length,
    homepageUnsafeGlobals: homepageUnsafeGlobals.length,
    homepageScopedPrimitiveOverrides: homepageScopedPrimitiveOverrides.length,
    campaignPolishPrimitiveOverrides: campaignPolishPrimitiveOverrides.length,
  },
  selectorGroups: selectorGroups.slice(0, 120),
  repeatedDeclarations: declarationGroups,
  vars: varGroups,
  homepageUnsafeGlobals: unique(homepageUnsafeGlobals),
  homepageScopedPrimitiveOverrides: unique(homepageScopedPrimitiveOverrides).slice(0, 160),
  campaignPolishPrimitiveOverrides: unique(campaignPolishPrimitiveOverrides).slice(0, 220),
  recommendations,
  checkedAt: new Date().toISOString(),
};

await fs.mkdir("artifacts/frontend-screenshots", { recursive: true });
await fs.writeFile(
  "artifacts/frontend-screenshots/css-duplication-audit.json",
  `${JSON.stringify(result, null, 2)}\n`
);

console.log("");
console.log("CSS duplication audit");
console.log("---------------------");
console.log(`Core rules: ${result.counts.rules.core}`);
console.log(`Homepage rules: ${result.counts.rules.homepage}`);
console.log(`Campaign polish rules: ${result.counts.rules.campaignPolish}`);
console.log(`Overlapping selectors: ${result.counts.overlappingSelectors}`);
console.log(`Repeated declarations: ${result.counts.repeatedDeclarations}`);
console.log(`Homepage unsafe global primitive overrides: ${result.counts.homepageUnsafeGlobals}`);
console.log(
  `Homepage scoped primitive overrides: ${result.counts.homepageScopedPrimitiveOverrides}`
);
console.log(
  `Campaign polish primitive overrides: ${result.counts.campaignPolishPrimitiveOverrides}`
);
console.log("");
console.log("Wrote artifacts/frontend-screenshots/css-duplication-audit.json");

if (!result.ok) {
  throw new Error(
    `CSS duplication audit failed: homepage has unscoped primitive/global overrides.\n${JSON.stringify(
      result.homepageUnsafeGlobals,
      null,
      2
    )}`
  );
}

console.log("✅ CSS duplication audit completed.");

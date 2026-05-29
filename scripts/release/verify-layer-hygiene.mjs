import fs from "node:fs/promises";

const cssPath = "apps/web/app/static/css/ff.css";
const css = await fs.readFile(cssPath, "utf8");

const requiredLayers = ["reset", "tokens", "base", "layout", "components", "campaign", "utilities"];
const failures = [];

const firstLayerLine = css.match(/@layer\s+([^;{]+);/);
if (!firstLayerLine) {
  failures.push("Missing global @layer declaration.");
} else {
  const declared = firstLayerLine[1].split(",").map((x) => x.trim());
  for (const layer of requiredLayers) {
    if (!declared.includes(layer)) failures.push(`Missing layer in declaration: ${layer}`);
  }
}

for (const layer of requiredLayers) {
  if (!css.includes(`@layer ${layer}`)) {
    failures.push(`Missing @layer block: ${layer}`);
  }
}

const markerPairs = [
  "FF HOMEPAGE MOBILE TAP TARGET FIX",
  "FF HOMEPAGE TAP TARGET FIX",
  "FF CAMPAIGN HEADER CONVERGENCE FIX",
  "FF FULL SUITE COMPATIBILITY",
];

for (const marker of markerPairs) {
  const start = css.match(new RegExp(`${marker} START`, "g")) || [];
  const end = css.match(new RegExp(`${marker} END`, "g")) || [];
  if (start.length !== end.length) {
    failures.push(`Marker mismatch: ${marker} start=${start.length} end=${end.length}`);
  }
}

const forbidden = [
  /^<<<<<<<(?: .*)?$/m,
  /^=======$/m,
  /^>>>>>>>(?: .*)?$/m,
  /!important\s*!important/,
];

for (const pattern of forbidden) {
  if (pattern.test(css)) {
    failures.push(`Forbidden CSS pattern found: ${pattern}`);
  }
}

await fs.mkdir("artifacts/release-proof", { recursive: true });
await fs.writeFile(
  "artifacts/release-proof/layer-hygiene.json",
  `${JSON.stringify(
    {
      ok: failures.length === 0,
      cssPath,
      checkedAt: new Date().toISOString(),
      requiredLayers,
      failures,
    },
    null,
    2
  )}\n`
);

if (failures.length) {
  throw new Error(`Layer hygiene failed:\n${failures.join("\n")}`);
}

console.log("✅ Layer hygiene is green.");

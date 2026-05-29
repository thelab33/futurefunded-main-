import fs from "node:fs";

const templatePath = "apps/web/app/templates/platform/index.html";
const template = fs.readFileSync(templatePath, "utf8");

const failures = [];

function assert(condition, message) {
  if (!condition) failures.push(message);
}

assert(
  template.includes("ff-platformPage ff-platformHomeV7") ||
    template.includes("ff-platformHomeV7 ff-platformPage"),
  "Platform root must include ff-platformHomeV7."
);

assert(
  template.includes("filename='css/ff.css'") || template.includes('filename="css/ff.css"'),
  "Platform template must load css/ff.css."
);

for (const forbidden of [
  "ff.homepage-flagship.css",
  "ff.ui-micropolish.css",
  "ff.campaign-polish.css",
]) {
  assert(!template.includes(forbidden), `Platform template must not load ${forbidden}.`);
}

for (const id of ["product", "campaigns", "sponsors", "operators", "faq"]) {
  assert(
    template.includes(`id="${id}"`) || template.includes(`id='${id}'`),
    `Missing required anchor target: #${id}`
  );
}

const navLabels = [
  ...template.matchAll(/<a[^>]*class="ff-primary-nav__link"[^>]*>([\s\S]*?)<\/a>/g),
]
  .map((m) => m[1].replace(/<[^>]+>/g, "").trim())
  .filter(Boolean);

const duplicates = navLabels.filter((label, index) => navLabels.indexOf(label) !== index);
assert(
  duplicates.length === 0,
  `Duplicate platform nav labels: ${[...new Set(duplicates)].join(", ")}`
);

if (failures.length) {
  console.error("❌ Platform markup contract failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("✅ Platform markup contract passed.");

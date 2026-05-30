#!/usr/bin/env node
import fs from "node:fs";
import { spawnSync } from "node:child_process";

const targets = [
  "apps/web/app/static/js/**/*.js",
  "scripts/**/*.mjs",
  "tests/**/*.js",
];

if (fs.existsSync("node_modules/.bin/eslint")) {
  const result = spawnSync("npx", ["eslint", ...targets], { stdio: "inherit" });
  process.exit(result.status ?? 1);
}

console.log("ℹ️ eslint not available; running syntax checks for key JS/MJS files.");

const files = [
  "scripts/campaign-payment-smoke.mjs",
  "scripts/campaign-payment-smoke-safe.mjs",
].filter((file) => fs.existsSync(file));

let failed = false;

for (const file of files) {
  const result = spawnSync("node", ["--check", file], { stdio: "inherit" });
  if (result.status !== 0) failed = true;
  else console.log(`✅ JS syntax: ${file}`);
}

process.exit(failed ? 1 : 0);

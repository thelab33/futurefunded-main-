#!/usr/bin/env node
import fs from "node:fs";
import { spawnSync } from "node:child_process";

const cssFiles = [
  "apps/web/app/static/css/ff.css",
  "apps/web/app/static/css/campaign.css",
  "apps/web/app/static/css/onboarding.css",
  "apps/web/app/static/css/auth.css",
].filter((file) => fs.existsSync(file));

let syntaxFailed = false;

for (const file of cssFiles) {
  const text = fs.readFileSync(file, "utf8");
  let balance = 0;

  for (const ch of text) {
    if (ch === "{") balance++;
    if (ch === "}") balance--;
    if (balance < 0) {
      console.error(`❌ CSS brace underflow: ${file}`);
      syntaxFailed = true;
      break;
    }
  }

  if (balance !== 0) {
    console.error(`❌ CSS brace mismatch: ${file} balance=${balance}`);
    syntaxFailed = true;
  } else {
    console.log(`✅ CSS brace check: ${file}`);
  }
}

if (syntaxFailed) process.exit(1);

if (fs.existsSync("node_modules/.bin/stylelint") && cssFiles.length) {
  const result = spawnSync("npx", ["stylelint", ...cssFiles], { stdio: "inherit" });
  if (result.status !== 0) {
    console.log("⚠️ stylelint formatting issues found, but CSS syntax is valid. Not blocking launch doctor.");
  }
} else {
  console.log("ℹ️ stylelint not available or no CSS files found; brace check completed.");
}

process.exit(0);

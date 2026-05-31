#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const OUT_DIR = path.join(ROOT, "audit_outputs", "campaign-payment-smoke");
const LATEST = path.join(OUT_DIR, "latest.json");
const BASE_URL = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const URL = `${BASE_URL}/c/connect-atx-elite`;

fs.mkdirSync(OUT_DIR, { recursive: true });

const checks = [];
const failures = [];

function check(name, ok, details = "") {
  checks.push({ name, ok: Boolean(ok), details });
  if (!ok) failures.push(`${name}${details ? `: ${details}` : ""}`);
}

async function main() {
  let html = "";
  let status = 0;

  try {
    const response = await fetch(`${URL}?campaign_payment_smoke=${Date.now()}`);
    status = response.status;
    html = await response.text();
  } catch (error) {
    check("campaign page fetch", false, String(error?.message || error));
  }

  check("campaign page status 200", status === 200, `status=${status}`);
  check("new campaign runtime rendered", html.includes("ff-campaign-runtime.js"));
  check("checkout direct rendered", html.includes("ff-checkout-direct.js"));
  check("old embedded checkout script removed", !html.includes("ff-embedded-checkout.js"));
  check("old campaign enterprise contract removed", !html.includes("ff-campaign-enterprise-contract.js"));
  check("checkout opener contract present", html.includes("data-ff-open-checkout"));
  check("checkout modal shell present", /id=["']checkout["']|data-ff-(embedded-)?checkout-(shell|sheet)/.test(html));

  const probe = spawnSync(
    "node",
    ["scripts/debug/ff_click_probe.mjs", "header [data-ff-open-checkout]"],
    {
      cwd: ROOT,
      encoding: "utf8",
      timeout: 45000,
      maxBuffer: 10 * 1024 * 1024,
    }
  );

  check("click probe command completed", probe.status === 0, `status=${probe.status}`);

  const tracePath = path.join(ROOT, "audit_outputs", "live-debug", "latest", "click-trace.json");
  let trace = null;

  try {
    trace = JSON.parse(fs.readFileSync(tracePath, "utf8"));
  } catch (error) {
    check("click trace json readable", false, String(error?.message || error));
  }

  if (trace) {
    check("checkout target found", trace.before?.found === true);
    check("checkout target not covered", trace.before?.covered === false);
    check("checkout click trial passes", !trace.trialError, trace.trialError || "");
    check("checkout real click passes", !trace.clickError, trace.clickError || "");
    check("checkout visible after click", trace.after?.checkout?.visible === true);
    check("checkout hidden false after click", trace.after?.checkout?.hidden === false);
    check("checkout aria-hidden false after click", trace.after?.checkout?.aria === "false");
    check("checkout state open after click", ["open", undefined, null].includes(trace.after?.checkout?.state) || trace.after?.checkout?.checkoutState === "open");
    check("campaign runtime loaded over network", (trace.network || []).some((row) => String(row.url || "").includes("ff-campaign-runtime.js")));
    check("checkout direct loaded over network", (trace.network || []).some((row) => String(row.url || "").includes("ff-checkout-direct.js")));
    check("stripe js loaded over network", (trace.network || []).some((row) => String(row.url || "").includes("js.stripe.com/v3")));
    check("no browser page errors", (trace.pageErrors || []).length === 0);
    check("no browser request failures", (trace.requestFailures || []).length === 0);
  }

  const result = {
    generatedAt: new Date().toISOString(),
    url: URL,
    status: failures.length ? "FAIL" : "PASS",
    checks,
    failures,
    probeStdout: probe.stdout || "",
    probeStderr: probe.stderr || "",
    tracePath,
  };

  fs.writeFileSync(LATEST, JSON.stringify(result, null, 2));

  console.log(`FutureFunded campaign money contract proof: ${result.status}`);
  console.log(`Results: ${LATEST}`);

  for (const item of checks) {
    console.log(`${item.ok ? "✅" : "❌"} ${item.name}${item.details ? ` — ${item.details}` : ""}`);
  }

  if (failures.length) {
    process.exit(1);
  }
}

main().catch((error) => {
  const result = {
    generatedAt: new Date().toISOString(),
    url: URL,
    status: "FAIL",
    checks,
    failures: [String(error?.stack || error?.message || error)],
  };
  fs.writeFileSync(LATEST, JSON.stringify(result, null, 2));
  console.error(result.failures[0]);
  process.exit(1);
});

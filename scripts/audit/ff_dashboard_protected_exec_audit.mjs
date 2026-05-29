import { chromium } from "playwright";
import fs from "node:fs";

const base = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || "";

const viewports = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 390, height: 1100 },
];

const results = [];

function record(ok, label, detail = "") {
  results.push({ ok: Boolean(ok), label, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? ` — ${detail}` : ""}`);
}

function protectedUrl() {
  const url = new URL("/platform/dashboard", base);
  if (token) url.searchParams.set("operator_token", token);
  url.searchParams.set("audit", `protected-exec-v7-${Date.now()}`);
  return url.toString();
}

function lockedUrl() {
  const url = new URL("/platform/dashboard", base);
  url.searchParams.set("audit", `locked-exec-v7-${Date.now()}`);
  return url.toString();
}

async function main() {
  const browser = await chromium.launch();

  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();

    const response = await page.goto(protectedUrl(), { waitUntil: "domcontentloaded", timeout: 45000 });
    const status = response?.status();
    const initialHtml = response ? await response.text() : "";

    record(status === 200, `Protected dashboard responds [${viewport.name}]`, `status=${status}`);

    const htmlWithoutTemplates = initialHtml.replace(/<template\b[^>]*>[\s\S]*?<\/template>/gi, "");
    const noPaintedAssistantOutsideTemplate =
      !/<section[^>]+class="[^"]*ff-launchAssistant/i.test(htmlWithoutTemplates);

    record(initialHtml.includes("data-ff-dashboard-exec-assistant-template"), `Launch assistant inert template present in response HTML [${viewport.name}]`);
    record(initialHtml.includes("data-ff-dashboard-exec-assistant-slot"), `Launch assistant slot present in response HTML [${viewport.name}]`);
    record(initialHtml.includes("exec-assistant-template-v7"), `Dashboard server layout contract v7 present [${viewport.name}]`);
    record(noPaintedAssistantOutsideTemplate, `Launch assistant absent outside inert template in response HTML [${viewport.name}]`);

    await page.waitForSelector("html.ff-dashboard-protected-exec-ready", { timeout: 5000 }).catch(() => null);

    const state = await page.evaluate(() => {
      const root = document.documentElement;
      const slot = document.querySelector("[data-ff-dashboard-exec-assistant-slot]");
      const template = document.querySelector("template[data-ff-dashboard-exec-assistant-template]");
      const assistant = slot?.querySelector("[data-ff-dashboard-launch-assistant], .ff-launchAssistant");
      const board = document.querySelector(".ff-dashboardModern__board");
      const topbar = document.querySelector(".ff-dashboardModern__topbar");
      const hero = document.querySelector(".ff-dashboardModern__hero");

      return {
        runtime: root.classList.contains("ff-dashboard-protected-exec"),
        ready: root.classList.contains("ff-dashboard-protected-exec-ready"),
        hardbootCleared: !root.classList.contains("ff-dashboard-hardboot"),
        bootingCleared: !root.classList.contains("ff-dashboard-protected-booting"),
        slot: Boolean(slot),
        template: Boolean(template),
        assistant: Boolean(assistant),
        compact: assistant?.dataset?.ffDashboardExecAssistant === "compact",
        executiveClass: Boolean(assistant?.classList?.contains("ff-dashboardExecutiveAssistant")),
        scripts: Boolean(
          assistant?.querySelector(".ff-launchAssistant__scripts") ||
          assistant?.textContent?.includes("Copy parent text")
        ),
        insideDashboard: Boolean(assistant?.closest(".ff-dashboardModern")),
        afterTopbar: Boolean(slot && topbar && topbar.compareDocumentPosition(slot) & Node.DOCUMENT_POSITION_FOLLOWING),
        afterHero: Boolean(slot && hero && hero.compareDocumentPosition(slot) & Node.DOCUMENT_POSITION_FOLLOWING),
        beforeBoard: Boolean(slot && board && slot.compareDocumentPosition(board) & Node.DOCUMENT_POSITION_FOLLOWING),
        cssLinks: [...document.querySelectorAll("link[rel='stylesheet'][href*='dashboard-modern.css']")].length,
        jsScripts: [...document.querySelectorAll("script[src*='ff-dashboard-protected-exec.js']")].length,
        overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
        heroHeight: hero?.getBoundingClientRect().height || 0,
        copy: document.body.innerText,
      };
    });

    record(state.runtime, `Executive runtime installed [${viewport.name}]`);
    record(state.ready, `Dashboard no-flash ready class present [${viewport.name}]`);
    record(state.hardbootCleared, `Dashboard hardboot class cleared [${viewport.name}]`);
    record(state.bootingCleared, `Dashboard booting class cleared [${viewport.name}]`);
    record(state.slot, `Launch assistant slot present [${viewport.name}]`);
    record(state.template, `Launch assistant inert template retained [${viewport.name}]`);
    record(state.assistant, `Launch assistant mounted from template [${viewport.name}]`);
    record(state.compact, `Launch assistant compact contract applied [${viewport.name}]`);
    record(state.executiveClass, `Launch assistant executive class applied [${viewport.name}]`);
    record(state.scripts, `Launch assistant scripts available [${viewport.name}]`);
    record(state.insideDashboard, `Launch assistant inside dashboard shell [${viewport.name}]`);
    record(state.afterTopbar, `Launch assistant appears after topbar [${viewport.name}]`);
    record(state.afterHero, `Launch assistant appears after hero [${viewport.name}]`);
    record(state.beforeBoard, `Launch assistant appears before command board [${viewport.name}]`);
    record(state.cssLinks >= 1, `Dashboard CSS authority linked [${viewport.name}]`, `count=${state.cssLinks}`);
    record(state.jsScripts === 1, `Executive dashboard JS linked [${viewport.name}]`, `count=${state.jsScripts}`);
    record(!state.overflowX, `No horizontal overflow [${viewport.name}]`, `overflow=${state.overflowX}`);
    record(state.heroHeight > 0 && state.heroHeight < (viewport.name === "mobile" ? 700 : 620), `Hero height controlled [${viewport.name}]`, `height=${Math.round(state.heroHeight)}`);

    for (const marker of [
      "Ready-to-send campaign scripts",
      "Next actions",
      "Operations & records",
    ]) {
      record(state.copy.includes(marker), `Dashboard copy marker remains: ${marker} [${viewport.name}]`);
    }

    record(
      state.copy.includes("Campaign command center") || state.copy.includes("Operator command center"),
      `Dashboard command-center copy marker remains [${viewport.name}]`
    );

    record(
      state.copy.includes("Launch quality") || state.copy.includes("Readiness"),
      `Dashboard launch-readiness copy marker remains [${viewport.name}]`
    );

    await context.close();
  }

  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();

    const response = await page.goto(lockedUrl(), { waitUntil: "domcontentloaded", timeout: 45000 });
    const status = response?.status();
    const state = await page.evaluate(() => ({
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      copy: document.body.innerText,
      cssLinks: [...document.querySelectorAll("link[href*='ff.css'], link[href*='login.css'], link[href*='ff-login-calm.css']")].length,
    }));

    record(status === 403, `Locked dashboard handoff responds [${viewport.name}]`, `status=${status}`);
    record(state.cssLinks >= 1, `Locked dashboard handoff loads protected access styles [${viewport.name}]`, `count=${state.cssLinks}`);
    record(!state.overflowX, `Locked dashboard handoff has no horizontal overflow [${viewport.name}]`, `overflow=${state.overflowX}`);
    record(state.copy.includes("Operator access required"), `Locked dashboard copy marker remains: Operator access required [${viewport.name}]`);
    record(state.copy.includes("Protected workspace"), `Locked dashboard copy marker remains: Protected workspace [${viewport.name}]`);
    record(!state.copy.includes("Sponsor review queue"), `Locked dashboard does not expose sponsor review queue [${viewport.name}]`);

    await context.close();
  }

  await browser.close();

  const jsSource = fs.readFileSync("apps/web/app/static/js/ff-dashboard-protected-exec.js", "utf8");
  for (const token of ["insertAdjacentElement", ".prepend(", "appendChild(wrap)", 'closest(".ff-dashboardModern")']) {
    record(!jsSource.includes(token), `Dashboard JS has no layout reparenting: ${token}`);
  }

  const passed = results.filter((r) => r.ok).length;
  const total = results.length;
  console.log(`\nSummary: ${passed}/${total} passed`);
  if (passed !== total) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

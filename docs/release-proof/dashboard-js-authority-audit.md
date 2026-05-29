# Dashboard JS Authority Audit

## Runtime references
apps/web/app/templates/platform/dashboard.html:18:  - ff-launch-completion.js
apps/web/app/templates/platform/dashboard.html:19:  - ff-dashboard-protected-exec.js
apps/web/app/templates/platform/dashboard.html:20:  - ff-operator-dashboard.js
apps/web/app/templates/platform/dashboard.html:601:  <script defer src="{{ url_for('static', filename='js/ff-launch-completion.js') }}?v={{ _asset_v|e }}"></script>
apps/web/app/templates/platform/dashboard.html:602:  <script defer src="{{ url_for('static', filename='js/ff-dashboard-protected-exec.js') }}?v={{ _asset_v|e }}" data-ff-dashboard-protected-exec-js></script>
apps/web/app/templates/platform/dashboard.html:603:  <script defer src="{{ url_for('static', filename='js/ff-operator-dashboard.js') }}?v={{ _asset_v|e }}" data-ff-operator-dashboard-js></script>
apps/web/app/templates/platform/onboarding.html:426:          src="{{ url_for('static', filename='js/ff-launch-completion.js') }}?v={{ asset_v|e }}"
apps/web/app/templates/platform/onboarding.html.bak.launch-workspace-contract-20260522092548:379:          src="{{ url_for('static', filename='js/ff-launch-completion.js') }}?v={{ asset_v|e }}"
apps/web/app/static/js/ff-launch-completion.js:3:  File: apps/web/app/static/js/ff-launch-completion.js

## JS file sizes
  678 apps/web/app/static/js/ff-operator-dashboard.js
   79 apps/web/app/static/js/ff-dashboard-protected-exec.js
  331 apps/web/app/static/js/ff-launch-completion.js
 1088 total

## Dashboard JS hooks
apps/web/app/static/js/ff-operator-dashboard.js:7:  const root = doc.querySelector("[data-ff-operator-root]");
apps/web/app/static/js/ff-operator-dashboard.js:12:  const $ = (selector, scope = doc) => scope.querySelector(selector);
apps/web/app/static/js/ff-operator-dashboard.js:13:  const $$ = (selector, scope = doc) => Array.from(scope.querySelectorAll(selector));
apps/web/app/static/js/ff-operator-dashboard.js:39:    ledgerHealth: $$("[data-ff-ledger-health]"),
apps/web/app/static/js/ff-operator-dashboard.js:40:    ledgerUpdated: $$("[data-ff-ledger-updated]"),
apps/web/app/static/js/ff-operator-dashboard.js:41:    raised: $$("[data-ff-op-raised]"),
apps/web/app/static/js/ff-operator-dashboard.js:42:    donationCount: $$("[data-ff-op-donation-count]"),
apps/web/app/static/js/ff-operator-dashboard.js:43:    sponsorCount: $$("[data-ff-op-sponsor-count]"),
apps/web/app/static/js/ff-operator-dashboard.js:44:    eventCount: $$("[data-ff-op-event-count]"),
apps/web/app/static/js/ff-operator-dashboard.js:45:    donationsTable: $("[data-ff-donations-table]"),
apps/web/app/static/js/ff-operator-dashboard.js:46:    sponsorsList: $("[data-ff-sponsors-list]"),
apps/web/app/static/js/ff-operator-dashboard.js:47:    eventsList: $("[data-ff-events-list]"),
apps/web/app/static/js/ff-operator-dashboard.js:48:    offlineForm: $("[data-ff-offline-donation-form]"),
apps/web/app/static/js/ff-operator-dashboard.js:49:    offlineStatus: $("[data-ff-offline-status]"),
apps/web/app/static/js/ff-operator-dashboard.js:50:    refreshButtons: $$("[data-ff-refresh-ledger]"),
apps/web/app/static/js/ff-operator-dashboard.js:51:    exportLinks: $$("[data-ff-export-url], [data-ff-export-csv]"),
apps/web/app/static/js/ff-operator-dashboard.js:180:    const response = await fetch(withOperatorToken(url), {
apps/web/app/static/js/ff-operator-dashboard.js:421:        new CustomEvent("ff:operator:hydrated", {
apps/web/app/static/js/ff-operator-dashboard.js:483:    const button = $("[data-ff-submit-offline-donation]", form);
apps/web/app/static/js/ff-operator-dashboard.js:513:        new CustomEvent("ff:operator:offline-recorded", {
apps/web/app/static/js/ff-operator-dashboard.js:533:      link.addEventListener("click", () => {
apps/web/app/static/js/ff-operator-dashboard.js:547:    doc.addEventListener("click", (event) => {
apps/web/app/static/js/ff-operator-dashboard.js:548:      const button = event.target.closest("[data-ff-refresh-ledger]");
apps/web/app/static/js/ff-operator-dashboard.js:570:    doc.addEventListener("submit", async (event) => {
apps/web/app/static/js/ff-operator-dashboard.js:571:      const form = event.target.closest("[data-ff-setup-status-form]");
apps/web/app/static/js/ff-operator-dashboard.js:576:      const row = form.closest("[data-ff-setup-row]");
apps/web/app/static/js/ff-operator-dashboard.js:577:      const select = form.querySelector("[data-ff-setup-status-select]");
apps/web/app/static/js/ff-operator-dashboard.js:578:      const button = form.querySelector('button[type="submit"]');
apps/web/app/static/js/ff-operator-dashboard.js:579:      const labelNode = row?.querySelector("[data-ff-setup-status-label]");
apps/web/app/static/js/ff-operator-dashboard.js:591:        const response = await fetch(form.action, {
apps/web/app/static/js/ff-operator-dashboard.js:621:          new CustomEvent("ff:operator:setup-status-updated", {
apps/web/app/static/js/ff-operator-dashboard.js:638:    doc.addEventListener("submit", (event) => {
apps/web/app/static/js/ff-operator-dashboard.js:639:      const form = event.target.closest("[data-ff-offline-donation-form]");
apps/web/app/static/js/ff-operator-dashboard.js:646:    nodes.offlineForm?.addEventListener("input", () => {
apps/web/app/static/js/ff-operator-dashboard.js:669:    doc.addEventListener("DOMContentLoaded", init, { once: true });
apps/web/app/static/js/ff-dashboard-protected-exec.js:11:    const slot = document.querySelector("[data-ff-dashboard-exec-assistant-slot]");
apps/web/app/static/js/ff-dashboard-protected-exec.js:12:    const template = document.querySelector("template[data-ff-dashboard-exec-assistant-template]");
apps/web/app/static/js/ff-dashboard-protected-exec.js:17:    const assistant = fragment.querySelector("[data-ff-dashboard-launch-assistant], .ff-launchAssistant");
apps/web/app/static/js/ff-dashboard-protected-exec.js:29:    document.querySelectorAll("[data-ff-copy-target]").forEach((button) => {
apps/web/app/static/js/ff-dashboard-protected-exec.js:33:      button.addEventListener("click", async () => {
apps/web/app/static/js/ff-dashboard-protected-exec.js:34:        const target = button.getAttribute("data-ff-copy-target");
apps/web/app/static/js/ff-dashboard-protected-exec.js:35:        const node = target ? document.querySelector(target) : null;
apps/web/app/static/js/ff-dashboard-protected-exec.js:71:    document.addEventListener("DOMContentLoaded", boot, { once: true });
apps/web/app/static/js/ff-launch-completion.js:19:    "[data-ff-onboard-root], [data-ff-dashboard-launch-assistant='p0-launch-completion']";
apps/web/app/static/js/ff-launch-completion.js:21:  const roots = Array.from(document.querySelectorAll(ROOT_SELECTOR));
apps/web/app/static/js/ff-launch-completion.js:40:    const status = root.querySelector("[data-ff-save-status]");
apps/web/app/static/js/ff-launch-completion.js:60:    String(scope?.querySelector(`[name="${name}"]`)?.value || "").trim();
apps/web/app/static/js/ff-launch-completion.js:75:    root.querySelectorAll("[data-ff-text-donate-setup]").forEach((scope) => {
apps/web/app/static/js/ff-launch-completion.js:76:      const preview = scope.querySelector("[data-ff-text-donate-preview]");
apps/web/app/static/js/ff-launch-completion.js:105:    root.addEventListener("click", async (event) => {
apps/web/app/static/js/ff-launch-completion.js:106:      const button = event.target.closest("[data-ff-copy-button]");
apps/web/app/static/js/ff-launch-completion.js:110:        button.closest("[data-ff-text-donate-setup], [data-ff-onboarding-text-to-donate], article, section") ||
apps/web/app/static/js/ff-launch-completion.js:114:        button.getAttribute("data-ff-copy-value") ||
apps/web/app/static/js/ff-launch-completion.js:119:        scope.querySelector("[data-ff-copy-source]") ||
apps/web/app/static/js/ff-launch-completion.js:120:        button.closest("article")?.querySelector("[data-ff-copy-source]") ||
apps/web/app/static/js/ff-launch-completion.js:121:        root.querySelector("[data-ff-copy-source]");
apps/web/app/static/js/ff-launch-completion.js:123:      const text = button.matches("[data-ff-copy-text-donate]")
apps/web/app/static/js/ff-launch-completion.js:162:    const fields = Array.from(form.querySelectorAll("input, select, textarea")).filter((field) => {
apps/web/app/static/js/ff-launch-completion.js:185:    const form = root.querySelector("[data-ff-form='launch-setup']");
apps/web/app/static/js/ff-launch-completion.js:191:    root.querySelectorAll("[data-ff-progress-value], [data-ff-progress-bucket]").forEach((meter) => {
apps/web/app/static/js/ff-launch-completion.js:197:    root.querySelectorAll("[data-ff-readiness-score]").forEach((node) => {
apps/web/app/static/js/ff-launch-completion.js:210:      window.localStorage.setItem(storageKey, JSON.stringify(payload));
apps/web/app/static/js/ff-launch-completion.js:212:      // localStorage may be disabled; the UI still confirms local in-page save.
apps/web/app/static/js/ff-launch-completion.js:219:      new CustomEvent("futurefunded:launch-setup-saved", {
apps/web/app/static/js/ff-launch-completion.js:229:      payload = JSON.parse(window.localStorage.getItem(storageKey) || "null");
apps/web/app/static/js/ff-launch-completion.js:237:      const fields = Array.from(form.querySelectorAll(`[name="${CSS.escape(key)}"]`));
apps/web/app/static/js/ff-launch-completion.js:256:    const form = root.querySelector("[data-ff-form='launch-setup']");
apps/web/app/static/js/ff-launch-completion.js:262:    form.addEventListener("input", () => {
apps/web/app/static/js/ff-launch-completion.js:268:    form.addEventListener("change", () => {
apps/web/app/static/js/ff-launch-completion.js:273:    root.addEventListener("click", (event) => {
apps/web/app/static/js/ff-launch-completion.js:274:      const button = event.target.closest("[data-ff-action='save-launch-setup']");
apps/web/app/static/js/ff-launch-completion.js:294:    root.addEventListener("click", (event) => {
apps/web/app/static/js/ff-launch-completion.js:298:      const target = document.querySelector(link.getAttribute("href"));
apps/web/app/static/js/ff-launch-completion.js:318:    root.addEventListener("input", () => updateTextDonatePreview(root));

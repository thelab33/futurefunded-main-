/* eslint no-unused-vars: ["error", { "argsIgnorePattern": "^_", "varsIgnorePattern": "^_", "caughtErrors": "none" }], no-empty: ["error", { "allowEmptyCatch": true }] */
(() => {
  "use strict";

  const win = window;
  const doc = document;
  const root = doc.querySelector("[data-ff-operator-root]");

  if (!root || win.__ffOperatorDashboard) return;
  win.__ffOperatorDashboard = true;

  const $ = (selector, scope = doc) => scope.querySelector(selector);
  const $$ = (selector, scope = doc) => Array.from(scope.querySelectorAll(selector));

  const urls = {
    ledger: root.dataset.ffLedgerUrl || "",
    events: root.dataset.ffEventsUrl || "",
    offline: root.dataset.ffOfflineUrl || "",
    export: root.dataset.ffExportUrl || "",
  };

  const query = new URLSearchParams(win.location.search);

  const operatorToken =
    root.dataset.ffOperatorToken ||
    query.get("operator_token") ||
    query.get("token") ||
    query.get("access_token") ||
    "";

  const state = {
    loading: false,
    lastSummary: null,
    lastEvents: [],
    lastError: null,
  };

  const nodes = {
    ledgerHealth: $$("[data-ff-ledger-health]"),
    ledgerUpdated: $$("[data-ff-ledger-updated]"),
    raised: $$("[data-ff-op-raised]"),
    donationCount: $$("[data-ff-op-donation-count]"),
    sponsorCount: $$("[data-ff-op-sponsor-count]"),
    eventCount: $$("[data-ff-op-event-count]"),
    donationsTable: $("[data-ff-donations-table]"),
    sponsorsList: $("[data-ff-sponsors-list]"),
    eventsList: $("[data-ff-events-list]"),
    offlineForm: $("[data-ff-offline-donation-form]"),
    offlineStatus: $("[data-ff-offline-status]"),
    refreshButtons: $$("[data-ff-refresh-ledger]"),
    exportLinks: $$("[data-ff-export-url], [data-ff-export-csv]"),
  };

  const numberFormat = new Intl.NumberFormat("en-US");
  const moneyFormat = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });

  const exactMoneyFormat = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });

  function text(value, fallback = "—") {
    const safe = String(value == null ? "" : value).trim();
    return safe || fallback;
  }

  function amountCents(value) {
    const amount = Number(value || 0);
    return Number.isFinite(amount) ? amount : 0;
  }

  function money(cents, options = {}) {
    const value = amountCents(cents) / 100;
    return options.exact ? exactMoneyFormat.format(value) : moneyFormat.format(value);
  }

  function amountInputToCents(value) {
    const raw = String(value || "").replace(/[^0-9.]/g, "");
    const amount = Number.parseFloat(raw);
    if (!Number.isFinite(amount) || amount <= 0) return 0;
    return Math.round(amount * 100);
  }

  function count(value) {
    const num = Number(value || 0);
    return numberFormat.format(Number.isFinite(num) ? num : 0);
  }

  function dateText(value) {
    if (!value) return "—";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";

    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function sentenceCase(value) {
    const safe = text(value, "").replace(/[_-]+/g, " ").trim();
    if (!safe) return "—";
    return safe.charAt(0).toUpperCase() + safe.slice(1);
  }

  function isEmail(value) {
    const safe = text(value, "");
    return !safe || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(safe);
  }

  function setText(targets, value) {
    const list = typeof targets === "string" ? $$(targets) : Array.from(targets || []);
    list.forEach((node) => {
      node.textContent = value;
    });
  }

  function setStatus(node, message, tone = "info") {
    if (!node) return;
    node.textContent = message;
    node.dataset.tone = tone;
  }

  function clearNode(node) {
    if (!node) return;
    node.replaceChildren();
  }

  function appendText(parent, tagName, value, className = "") {
    const node = doc.createElement(tagName);
    if (className) node.className = className;
    node.textContent = value;
    parent.appendChild(node);
    return node;
  }

  function setBusy(isBusy, label = "Refreshing…") {
    state.loading = Boolean(isBusy);
    root.dataset.ffOperatorLoading = String(state.loading);

    nodes.refreshButtons.forEach((button) => {
      button.disabled = state.loading;
      if (!button.dataset.ffIdleText) {
        button.dataset.ffIdleText = button.textContent.trim() || "Refresh";
      }
      button.textContent = state.loading ? label : button.dataset.ffIdleText;
    });
  }

  function operatorHeaders() {
    return operatorToken ? { "X-FF-Operator-Token": operatorToken } : {};
  }

  function withOperatorToken(url) {
    if (!url || !operatorToken) return url;

    try {
      const next = new URL(url, win.location.origin);
      if (!next.searchParams.has("operator_token")) {
        next.searchParams.set("operator_token", operatorToken);
      }
      return next.toString();
    } catch {
      return url;
    }
  }

  async function fetchJson(url, options = {}) {
    if (!url) throw new Error("Missing dashboard endpoint.");

    const method = options.method || "GET";
    const response = await fetch(withOperatorToken(url), {
      credentials: "same-origin",
      method,
      headers: {
        Accept: "application/json",
        ...(method !== "GET" ? { "Content-Type": "application/json" } : {}),
        ...operatorHeaders(),
        ...(options.headers || {}),
      },
      ...options,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const message =
        data.error ||
        data.message ||
        data.detail ||
        `Request failed with ${response.status}`;
      throw new Error(message);
    }

    return data;
  }

  function getArray(payload, ...keys) {
    for (const key of keys) {
      if (Array.isArray(payload?.[key])) return payload[key];
    }
    return [];
  }

  function normalizeSummary(payload) {
    const totals = payload?.totals || payload?.summary || {};

    return {
      raw: payload || {},
      totals,
      donations: getArray(payload, "recentDonations", "recent_donations", "donations"),
      sponsors: getArray(payload, "recentSponsors", "recent_sponsors", "sponsors"),
    };
  }

  function setLedgerHealth(status, message, tone = "info") {
    setText(nodes.ledgerHealth, status);
    setText(nodes.ledgerUpdated, message);
    root.dataset.ffLedgerTone = tone;
  }

  function renderLoadingRows() {
    if (nodes.donationsTable) {
      nodes.donationsTable.innerHTML = '<tr><td colspan="5">Loading donations…</td></tr>';
    }

    if (nodes.sponsorsList) {
      nodes.sponsorsList.innerHTML = '<article class="ff-opEmpty">Loading sponsor orders…</article>';
    }

    if (nodes.eventsList) {
      nodes.eventsList.innerHTML = '<article class="ff-opEmpty">Loading payment events…</article>';
    }
  }

  function renderEmptyTable(message) {
    if (!nodes.donationsTable) return;

    const tr = doc.createElement("tr");
    const td = doc.createElement("td");
    td.colSpan = 5;
    td.textContent = message;
    tr.appendChild(td);

    nodes.donationsTable.replaceChildren(tr);
  }

  function renderDonations(donations) {
    if (!nodes.donationsTable) return;

    if (!donations.length) {
      renderEmptyTable("No completed donations yet. New gifts will appear here after payment confirmation.");
      return;
    }

    const fragment = doc.createDocumentFragment();

    donations.slice(0, 20).forEach((row) => {
      const tr = doc.createElement("tr");

      const amount = doc.createElement("td");
      appendText(amount, "strong", money(row.amount_cents ?? row.amountCents));

      const donor = doc.createElement("td");
      donor.textContent = text(row.donor_name || row.donor_email || row.customer_email, "Anonymous/supporter");

      const status = doc.createElement("td");
      const statusPill = doc.createElement("span");
      statusPill.className = "ff-opStatus";
      statusPill.dataset.status = text(row.status, "unknown").toLowerCase();
      statusPill.textContent = sentenceCase(row.status || "succeeded");
      status.appendChild(statusPill);

      const provider = doc.createElement("td");
      provider.textContent = sentenceCase(row.provider || "stripe");

      const created = doc.createElement("td");
      created.textContent = dateText(row.created_at || row.createdAt || row.created);

      tr.append(amount, donor, status, provider, created);
      fragment.appendChild(tr);
    });

    nodes.donationsTable.replaceChildren(fragment);
  }

  function renderSponsors(sponsors) {
    if (!nodes.sponsorsList) return;

    if (!sponsors.length) {
      nodes.sponsorsList.innerHTML =
        '<article class="ff-opEmpty">No sponsor orders yet. Sponsor packages will appear here after payment confirmation.</article>';
      return;
    }

    const fragment = doc.createDocumentFragment();

    sponsors.slice(0, 12).forEach((row) => {
      const article = doc.createElement("article");
      article.className = "ff-opSponsor";

      const main = doc.createElement("div");
      appendText(main, "span", sentenceCase(row.sponsor_tier || row.package_name || "Sponsor"));
      appendText(main, "strong", text(row.business_name || row.sponsor_name || row.contact_email, "Pending sponsor"));
      appendText(main, "p", text(row.contact_email || row.email, "No contact email"));

      const meta = doc.createElement("div");
      appendText(meta, "strong", money(row.amount_cents ?? row.amountCents));
      appendText(meta, "em", sentenceCase(row.fulfillment_status || row.status || "pending review"));

      article.append(main, meta);
      fragment.appendChild(article);
    });

    nodes.sponsorsList.replaceChildren(fragment);
  }

  function renderEvents(events) {
    if (!nodes.eventsList) return;

    setText(nodes.eventCount, count(events.length));

    if (!events.length) {
      nodes.eventsList.innerHTML =
        '<article class="ff-opEmpty">No provider events recorded yet. Payment activity will appear here after checkout/webhook processing.</article>';
      return;
    }

    const fragment = doc.createDocumentFragment();

    events.slice(0, 18).forEach((row) => {
      const article = doc.createElement("article");
      article.className = "ff-opEvent";

      const main = doc.createElement("div");
      appendText(main, "strong", sentenceCase(row.event_type || row.type || "payment event"));

      const eventId = text(row.provider_event_id || row.event_id || row.id, "");
      if (eventId) appendText(main, "span", eventId);

      const processed =
        row.processed_at ||
        row.created_at ||
        row.created ||
        row.updated_at;

      appendText(
        article,
        "em",
        `${sentenceCase(row.status || "processed")} · ${dateText(processed)}`
      );

      article.prepend(main);
      fragment.appendChild(article);
    });

    nodes.eventsList.replaceChildren(fragment);
  }

  function renderTotals(summary, events = state.lastEvents) {
    const totals = summary.totals || {};

    setText(nodes.raised, money(totals.raised_amount_cents ?? totals.raisedAmountCents));
    setText(nodes.donationCount, count(totals.donation_count ?? totals.donationCount));
    setText(nodes.sponsorCount, count(totals.sponsor_count ?? totals.sponsorCount));
    setText(nodes.eventCount, count(events.length || totals.event_count || totals.eventCount));

    const updated =
      totals.updated_at ||
      totals.updatedAt ||
      summary.raw.updated_at ||
      summary.raw.updatedAt;

    setLedgerHealth(
      "Ledger online",
      updated ? `Updated ${dateText(updated)}` : "Ledger loaded. No update timestamp returned.",
      "success"
    );
  }

  async function hydrate(options = {}) {
    if (state.loading && !options.force) return state.lastSummary;

    setBusy(true, options.label || "Refreshing…");

    if (!state.lastSummary) {
      renderLoadingRows();
      setLedgerHealth("Checking ledger…", "Loading latest campaign records.", "info");
    }

    try {
      const summaryPayload = await fetchJson(urls.ledger);
      const summary = normalizeSummary(summaryPayload);
      state.lastSummary = summary;
      state.lastError = null;

      renderDonations(summary.donations);
      renderSponsors(summary.sponsors);

      let events = [];
      try {
        const eventPayload = await fetchJson(urls.events);
        events = getArray(eventPayload, "events", "recentEvents", "recent_events");
      } catch {
        events = [];
      }

      state.lastEvents = events;
      renderEvents(events);
      renderTotals(summary, events);

      doc.dispatchEvent(
        new CustomEvent("ff:operator:hydrated", {
          detail: {
            summary: summary.raw,
            totals: summary.totals,
            donations: summary.donations,
            sponsors: summary.sponsors,
            events,
          },
        })
      );

      return summary;
    } catch (error) {
      state.lastError = error;
      setLedgerHealth("Ledger unavailable", error.message || "Could not load ledger.", "warning");

      if (!state.lastSummary) {
        renderEmptyTable("Could not load donations. Refresh the ledger or check the campaign endpoint.");
        if (nodes.sponsorsList) {
          nodes.sponsorsList.innerHTML =
            '<article class="ff-opEmpty">Could not load sponsor orders.</article>';
        }
        if (nodes.eventsList) {
          nodes.eventsList.innerHTML =
            '<article class="ff-opEmpty">Could not load payment events.</article>';
        }
      }

      throw error;
    } finally {
      setBusy(false);
    }
  }

  function offlinePayload(form) {
    return {
      amount: form.elements.amount?.value || "",
      donor_name: form.elements.donor_name?.value || "",
      donor_email: form.elements.donor_email?.value || "",
      note: form.elements.note?.value || "",
    };
  }

  function validateOfflinePayload(payload, form) {
    const cents = amountInputToCents(payload.amount);

    if (!cents) {
      setStatus(nodes.offlineStatus, "Enter an offline amount greater than $0.", "warning");
      form.elements.amount?.focus();
      return false;
    }

    if (payload.donor_email && !isEmail(payload.donor_email)) {
      setStatus(nodes.offlineStatus, "Enter a valid donor email, or leave it blank.", "warning");
      form.elements.donor_email?.focus();
      return false;
    }

    return true;
  }

  async function submitOfflineDonation(form) {
    const button = $("[data-ff-submit-offline-donation]", form);
    const payload = offlinePayload(form);

    if (!validateOfflinePayload(payload, form)) return;

    if (button) {
      button.disabled = true;
      button.dataset.ffIdleText = button.dataset.ffIdleText || button.textContent.trim();
      button.textContent = "Recording support…";
    }

    setStatus(nodes.offlineStatus, "Recording offline support…", "info");

    try {
      const result = await fetchJson(urls.offline, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const recordedCents =
        result.amount_cents ??
        result.amountCents ??
        amountInputToCents(payload.amount);

      form.reset();
      setStatus(nodes.offlineStatus, `Recorded ${money(recordedCents, { exact: true })} offline support.`, "success");

      await hydrate({ force: true, label: "Updating…" });

      doc.dispatchEvent(
        new CustomEvent("ff:operator:offline-recorded", {
          detail: result,
        })
      );
    } catch (error) {
      setStatus(nodes.offlineStatus, error.message || "Could not record offline support.", "warning");
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = button.dataset.ffIdleText || "Add offline donation";
      }
    }
  }

  function wireExportLinks() {
    nodes.exportLinks.forEach((link) => {
      if (!link || !urls.export) return;

      link.href = withOperatorToken(urls.export);

      link.addEventListener("click", () => {
        link.dataset.ffExportClicked = "true";
        const old = link.textContent;
        link.textContent = "Preparing CSV…";

        win.setTimeout(() => {
          link.textContent = old;
          delete link.dataset.ffExportClicked;
        }, 1400);
      });
    });
  }

  function wireRefreshButtons() {
    doc.addEventListener("click", (event) => {
      const button = event.target.closest("[data-ff-refresh-ledger]");
      if (!button) return;

      event.preventDefault();

      hydrate({ force: true, label: "Refreshing…" }).catch(() => {});
    });
  }

  function setupStatusLabel(status) {
    const labels = {
      draft: "Draft",
      review_needed: "Review Needed",
      launch_ready: "Launch Ready",
      launched: "Launched",
      archived: "Archived",
    };

    return labels[status] || sentenceCase(status || "draft");
  }

  function wireSetupStatusForms() {
    doc.addEventListener("submit", async (event) => {
      const form = event.target.closest("[data-ff-setup-status-form]");
      if (!form) return;

      event.preventDefault();

      const row = form.closest("[data-ff-setup-row]");
      const select = form.querySelector("[data-ff-setup-status-select]");
      const button = form.querySelector('button[type="submit"]');
      const labelNode = row?.querySelector("[data-ff-setup-status-label]");
      const nextStatus = select?.value || "draft";

      if (!form.action) return;

      if (button) {
        button.disabled = true;
        button.dataset.ffIdleText = button.dataset.ffIdleText || button.textContent.trim();
        button.textContent = "Saving…";
      }

      try {
        const response = await fetch(form.action, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
            ...operatorHeaders(),
          },
          body: JSON.stringify({ status: nextStatus }),
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok || data.ok === false) {
          throw new Error(data.message || `Status update failed with ${response.status}`);
        }

        const savedStatus = data.status || nextStatus;
        const savedLabel = data.label || setupStatusLabel(savedStatus);

        if (row) row.dataset.ffSetupStatus = savedStatus;

        if (labelNode) {
          labelNode.dataset.status = savedStatus;
          labelNode.textContent = savedLabel;
        }

        setLedgerHealth("Setup updated", data.message || `Moved setup to ${savedLabel}.`, "success");

        doc.dispatchEvent(
          new CustomEvent("ff:operator:setup-status-updated", {
            detail: data,
          })
        );
      } catch (error) {
        setLedgerHealth("Setup update failed", error.message || "Could not update setup status.", "warning");
      } finally {
        if (button) {
          button.disabled = false;
          button.textContent = button.dataset.ffIdleText || "Update";
        }
      }
    });
  }


  function wireOfflineForm() {
    doc.addEventListener("submit", (event) => {
      const form = event.target.closest("[data-ff-offline-donation-form]");
      if (!form) return;

      event.preventDefault();
      submitOfflineDonation(form);
    });

    nodes.offlineForm?.addEventListener("input", () => {
      if (!nodes.offlineStatus) return;
      if (nodes.offlineStatus.dataset.tone === "warning") {
        nodes.offlineStatus.textContent = "";
        delete nodes.offlineStatus.dataset.tone;
      }
    });
  }

  function init() {
    wireExportLinks();
    wireRefreshButtons();
    wireSetupStatusForms();
    wireOfflineForm();

    if (urls.ledger) {
      hydrate({ force: true, label: "Loading…" }).catch(() => {});
    } else {
      setLedgerHealth("Ledger endpoint missing", "Dashboard shell loaded, but no ledger endpoint is configured.", "info");
    }
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }

  win.FutureFundedOperatorDashboard = {
    refresh: () => hydrate({ force: true }),
    getState: () => ({ ...state }),
  };
})();

/* ==========================================================================
   FF_DASHBOARD_PROTECTED_EXEC_FOLDED_V1
   Dashboard-only assistant mount + copy-target helpers.
   Folded into ff-operator-dashboard.js so dashboard has one JS authority.
   ========================================================================== */
(() => {
  "use strict";

  const bootProtectedAssistant = () => {
    const root = document.querySelector("[data-ff-operator-root]");
    if (!root) return;

    const slot = document.querySelector("[data-ff-dashboard-exec-assistant-slot]");
    const template = document.querySelector("template[data-ff-dashboard-exec-assistant-template]");

    if (slot && template && slot.dataset.ffAssistantMounted !== "true") {
      const fragment = template.content.cloneNode(true);
      slot.replaceChildren(fragment);
      slot.dataset.ffAssistantMounted = "true";

      const assistant = slot.querySelector("[data-ff-dashboard-launch-assistant], .ff-launchAssistant");
      if (assistant) {
        assistant.setAttribute("data-ff-dashboard-assistant-mounted", "true");
      }

      document.dispatchEvent(
        new CustomEvent("ff:dashboard:assistant-mounted", {
          bubbles: true,
          detail: { mounted: true },
        })
      );
    }

    document.querySelectorAll("[data-ff-copy-target]").forEach((button) => {
      if (button.dataset.ffCopyTargetBound === "true") return;
      button.dataset.ffCopyTargetBound = "true";

      button.addEventListener("click", async () => {
        const target = button.getAttribute("data-ff-copy-target");
        const node = target ? document.querySelector(target) : null;
        const value = node
          ? ("value" in node ? node.value : node.textContent || "")
          : "";

        const text = String(value || "").trim();
        if (!text) return;

        const originalLabel = button.textContent;

        try {
          if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
          } else {
            const scratch = document.createElement("textarea");
            scratch.value = text;
            scratch.setAttribute("readonly", "");
            scratch.style.position = "fixed";
            scratch.style.inset = "auto auto 0 0";
            scratch.style.opacity = "0";
            document.body.appendChild(scratch);
            scratch.select();
            document.execCommand("copy");
            scratch.remove();
          }

          button.textContent = "Copied";
          button.setAttribute("data-ff-copy-state", "copied");

          window.setTimeout(() => {
            button.textContent = originalLabel || "Copy";
            button.removeAttribute("data-ff-copy-state");
          }, 1600);
        } catch (error) {
          button.textContent = "Copy failed";
          button.setAttribute("data-ff-copy-state", "error");

          window.setTimeout(() => {
            button.textContent = originalLabel || "Copy";
            button.removeAttribute("data-ff-copy-state");
          }, 1800);
        }
      });
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootProtectedAssistant, { once: true });
  } else {
    bootProtectedAssistant();
  }
})();
/* ==========================================================================
   FutureFunded HOI 6G.1 — Operator Dashboard Control Names
   Marker: hoi-6g1-operator-dashboard-control-names-v1

   Intent:
   - preserve dashboard visuals and hooks
   - give every visible icon/empty dashboard control a stable accessible name
   - clear visual launch gate UNNAMED_CONTROLS for token dashboard
========================================================================== */
(function enhanceFutureFundedOperatorControlNames() {
  "use strict";

  var ROOT_SELECTOR = [
    "[data-ff-operator-root]",
    "[data-ff-dashboard-root]",
    ".ff-dashboardPage",
    ".ff-dashboardModern",
    ".ff-operatorPage",
    ".ff-operatorDashboard"
  ].join(",");

  var CONTROL_SELECTOR = [
    "a",
    "button",
    "[role='button']",
    "input[type='submit']",
    "input[type='button']"
  ].join(",");

  function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function isVisible(el) {
    if (!el || !(el instanceof HTMLElement)) return false;
    var style = window.getComputedStyle(el);
    var rect = el.getBoundingClientRect();

    return (
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      rect.width > 0 &&
      rect.height > 0
    );
  }

  function hasName(el) {
    return Boolean(
      clean(el.getAttribute("aria-label")) ||
      clean(el.getAttribute("title")) ||
      clean(el.innerText) ||
      clean(el.getAttribute("value"))
    );
  }

  function titleCase(value) {
    return clean(value)
      .replace(/^data-ff-/, "")
      .replace(/[-_]+/g, " ")
      .replace(/\b\w/g, function (char) {
        return char.toUpperCase();
      });
  }

  function nearestHeading(el) {
    var card = el.closest(
      ".ff-card,.ff-panel,.ff-surface,.ff-dashboardCard,.ff-dashboardModern__card,.ff-dashboardModern__metric,.ff-ledgerCard,.ff-sponsorCard,section,article"
    );

    if (!card) return "";

    var heading = card.querySelector("h1,h2,h3,h4,.ff-cardTitle,.ff-panelTitle,.ff-sectionTitle,.ff-dashboardModern__sectionTitle,.ff-dashboardModern__metricLabel");
    return clean(heading && heading.innerText);
  }

  function inferFromHooks(el) {
    var attrs = Array.prototype.slice.call(el.attributes || []);

    for (var i = 0; i < attrs.length; i += 1) {
      var attr = attrs[i];

      if (!attr.name.startsWith("data-ff")) continue;

      var key = attr.name + (attr.value ? "=" + attr.value : "");

      if (/refresh.*ledger|ledger.*refresh/i.test(key)) return "Refresh ledger";
      if (/export.*ledger|ledger.*export/i.test(key)) return "Export ledger";
      if (/offline.*donation|donation.*offline/i.test(key)) return "Record offline donation";
      if (/sponsor.*section|open.*sponsor|sponsor.*open/i.test(key)) return "Open sponsor section";
      if (/sponsor.*review|review.*sponsor/i.test(key)) return "Review sponsors";
      if (/public.*campaign|campaign.*public/i.test(key)) return "Open public campaign";
      if (/copy/i.test(key)) return "Copy";
      if (/share/i.test(key)) return "Share campaign";
      if (/close/i.test(key)) return "Close panel";
      if (/menu/i.test(key)) return "Open menu";
      if (/toggle/i.test(key)) return "Toggle details";
      if (/submit/i.test(key)) return "Submit form";
      if (/save/i.test(key)) return "Save changes";
      if (/edit/i.test(key)) return "Edit setup";
    }

    return "";
  }

  function inferFromHref(el) {
    var href = clean(el.getAttribute("href"));
    if (!href) return "";

    if (/\/c\/|campaign/i.test(href)) return "Open public campaign";
    if (/ledger.*export|export/i.test(href)) return "Export ledger";
    if (/sponsor/i.test(href)) return "Open sponsor section";
    if (/dashboard/i.test(href)) return "Open dashboard";
    if (/platform\/onboarding|setup/i.test(href)) return "Continue launch setup";

    return "";
  }

  function inferFromType(el) {
    var type = clean(el.getAttribute("type")).toLowerCase();

    if (type === "submit") {
      var form = el.closest("form");
      var formText = clean(form && form.innerText).toLowerCase();

      if (/offline|donation/.test(formText)) return "Record offline donation";
      if (/sponsor/.test(formText)) return "Save sponsor";
      if (/setup|campaign/.test(formText)) return "Save campaign setup";

      return "Submit form";
    }

    return "";
  }

  function inferLabel(el) {
    var explicit =
      inferFromHooks(el) ||
      inferFromHref(el) ||
      inferFromType(el);

    if (explicit) return explicit;

    var heading = nearestHeading(el);
    if (heading) return "Open " + heading;

    var dataAction = clean(el.getAttribute("data-action") || el.getAttribute("data-ff-action"));
    if (dataAction) return titleCase(dataAction);

    var className = clean(el.className);
    if (/close/i.test(className)) return "Close panel";
    if (/menu/i.test(className)) return "Open menu";
    if (/toggle/i.test(className)) return "Toggle details";
    if (/icon/i.test(className)) return "Open dashboard action";

    return "Dashboard action";
  }

  function enhance(root) {
    var scopes = [];

    if (root && root.matches && root.matches(ROOT_SELECTOR)) {
      scopes.push(root);
    }

    if (root && root.querySelectorAll) {
      scopes = scopes.concat(Array.prototype.slice.call(root.querySelectorAll(ROOT_SELECTOR)));
    }

    if (!scopes.length && document.querySelector(ROOT_SELECTOR)) {
      scopes = Array.prototype.slice.call(document.querySelectorAll(ROOT_SELECTOR));
    }

    scopes.forEach(function (scope) {
      var controls = Array.prototype.slice.call(scope.querySelectorAll(CONTROL_SELECTOR));

      controls.forEach(function (control) {
        if (!isVisible(control)) return;
        if (hasName(control)) return;

        var label = inferLabel(control);

        control.setAttribute("aria-label", label);
        control.setAttribute("title", label);
        control.setAttribute("data-ff-a11y-label", "operator-control");
      });
    });
  }

  function start() {
    enhance(document);

    try {
      var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
          mutation.addedNodes.forEach(function (node) {
            if (node && node.nodeType === 1) {
              enhance(node);
            }
          });
        });
      });

      observer.observe(document.documentElement, {
        childList: true,
        subtree: true
      });
    } catch (_) {
      /* Progressive enhancement only. */
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();

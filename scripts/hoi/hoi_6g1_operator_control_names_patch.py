#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()
JS = ROOT / "apps/web/app/static/js/ff-operator-dashboard.js"
MARKER = "hoi-6g1-operator-dashboard-control-names-v1"

BLOCK = r'''

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
'''

if not JS.exists():
    raise SystemExit(f"Missing dashboard JS file: {JS}")

text = JS.read_text(errors="ignore")

if MARKER in text:
    print(f"Already patched: {JS}")
else:
    backup = JS.with_suffix(JS.suffix + f".bak-hoi6g1-{time.strftime('%Y%m%d%H%M%S')}")
    backup.write_text(text)
    JS.write_text(text.rstrip() + "\n" + BLOCK.strip() + "\n")
    print(f"Patched: {JS}")
    print(f"Backup:  {backup}")

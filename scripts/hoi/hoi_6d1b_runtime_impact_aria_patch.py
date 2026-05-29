#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()
JS = ROOT / "apps/web/app/static/js/ff-campaign.js"
MARKER = "hoi-6d1b-runtime-impact-aria-labels-v1"

BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6D.1B — Runtime Impact CTA Semantic Labels
   Marker: hoi-6d1b-runtime-impact-aria-labels-v1

   Why:
   - Impact donation cards can keep rich visual copy.
   - The accessible control name should stay concise: “Donate $25”.
   - Preserve all data-ff hooks and checkout behavior.
========================================================================== */
(function enhanceFutureFundedImpactDonationLabels() {
  "use strict";

  var SELECTOR = [
    '[data-ff-amount-button="impact"]',
    '[data-ff-donation-amount]',
    '[data-ff-open-checkout]',
    '[data-ff-donate-trigger]',
    '[data-ff-payment-trigger]'
  ].join("");

  function formatAmount(raw) {
    var value = String(raw || "").trim();
    if (!value) return "";

    value = value.replace(/[$,\s]/g, "");
    var number = Number(value);

    if (!Number.isFinite(number) || number <= 0) {
      return "";
    }

    if (Number.isInteger(number)) {
      return String(number);
    }

    return number.toFixed(2).replace(/\.00$/, "");
  }

  function getAmount(button) {
    return (
      button.getAttribute("data-ff-donation-amount") ||
      button.getAttribute("data-ff-checkout-amount") ||
      button.getAttribute("data-ff-amount") ||
      ""
    );
  }

  function enhance(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var buttons = scope.querySelectorAll(SELECTOR);

    buttons.forEach(function (button) {
      if (!(button instanceof HTMLElement)) return;

      var existing = (button.getAttribute("aria-label") || "").trim();
      if (existing) return;

      var amount = formatAmount(getAmount(button));
      if (!amount) return;

      button.setAttribute("aria-label", "Donate $" + amount);
      button.setAttribute("data-ff-aria-enhanced", "impact-donation");
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
      /* MutationObserver is progressive enhancement only. */
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
    raise SystemExit(f"Missing {JS}")

text = JS.read_text(errors="ignore")

if MARKER in text:
    print(f"Already patched: {JS}")
else:
    backup = JS.with_suffix(JS.suffix + f".bak-hoi6d1b-{time.strftime('%Y%m%d%H%M%S')}")
    backup.write_text(text)
    JS.write_text(text.rstrip() + "\n" + BLOCK.strip() + "\n")
    print(f"Patched: {JS}")
    print(f"Backup:  {backup}")

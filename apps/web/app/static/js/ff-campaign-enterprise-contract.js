/*
  FutureFunded campaign enterprise modal contract
  Marker: hoi-9b-campaign-enterprise-contract-external-v1
  Purpose:
  - CSP-safe external runtime
  - deterministic checkout/sponsor/share open state
  - preserves existing data-ff hooks
*/
(() => {
  "use strict";

  const REGISTRY = {
    checkout: {
      modal:
        "#checkout,[data-ff-embedded-checkout-shell],[data-ff-checkout-sheet],[data-ff-checkout-modal],[data-ff-donation-modal],.ff-embeddedCheckout,.ff-checkoutModal",
      panel:
        "[data-ff-embedded-checkout-panel],.ff-embeddedCheckout__panel,.ff-checkoutModal__panel,[role='dialog']",
      open: "[data-ff-open-checkout],[data-ff-donate-trigger],[data-ff-payment-trigger],[data-ff-donate-submit],[data-ff-start-embedded-checkout]",
      close:
        "[data-ff-close-embedded-checkout],[data-ff-checkout-close],[data-ff-close-checkout],[aria-label='Close checkout']",
      rootClass: "ff-checkout-open",
      stateAttr: "data-ff-checkout-state",
    },
    sponsor: {
      modal:
        "#sponsor-modal,[data-ff-sponsor-modal],[data-ff-sponsor-sheet],[data-ff-sponsor-drawer],[data-ff-sponsor-panel],.ff-sponsorModal",
      panel: ".ff-sponsorModal__panel,[data-ff-sponsor-panel],[role='dialog']",
      open: "[data-ff-open-sponsor],[data-ff-sponsor-trigger],[data-ff-sponsor-cta]",
      close: "[data-ff-sponsor-close],[data-ff-close-sponsor],[aria-label='Close sponsor options']",
      rootClass: "ff-sponsor-open",
      stateAttr: "data-ff-sponsor-state",
    },
    share: {
      modal: "#qr-modal,[data-ff-share-drawer],[data-ff-qr-modal],.ff-shareDrawer",
      panel: ".ff-shareDrawer__panel,[data-ff-share-panel],[role='dialog']",
      open: "[data-ff-share-trigger],[data-ff-qr-trigger],[data-ff-share]",
      close: "[data-ff-share-close],[data-ff-close-qr-modal],[aria-label='Close share drawer']",
      rootClass: "ff-share-open",
      stateAttr: "data-ff-share-state",
    },
  };

  /*
    Marker: hoi-9c-sponsor-modal-fallback-v1
    Some campaign builds expose sponsor CTAs before the sponsor modal is present.
    This creates a small, production-safe modal shell so sponsor interest never dead-ends.
  */
  const ensureSponsorModal = () => {
    let node = document.querySelector("#sponsor-modal");

    if (node) {
      node.setAttribute("data-ff-sponsor-modal", "true");
      return node;
    }

    const campaignName =
      document.querySelector("[data-ff-campaign-title]")?.textContent?.trim() ||
      document.querySelector("h1")?.textContent?.replace(/\s+/g, " ").trim() ||
      "this campaign";

    node = document.createElement("div");
    node.id = "sponsor-modal";
    node.className = "ff-sponsorModal";
    node.hidden = true;
    node.setAttribute("hidden", "");
    node.setAttribute("aria-hidden", "true");
    node.setAttribute("data-ff-sponsor-modal", "true");
    node.setAttribute("data-ff-state", "closed");
    node.setAttribute("data-ff-modal-state", "closed");
    node.setAttribute("data-ff-sponsor-state", "closed");

    node.innerHTML = `
      <div class="ff-sponsorModal__backdrop" data-ff-sponsor-close aria-hidden="true"></div>
      <section class="ff-sponsorModal__panel" role="dialog" aria-modal="true" aria-labelledby="ff-sponsor-modal-title" tabindex="-1">
        <button class="ff-sponsorModal__close" type="button" data-ff-sponsor-close aria-label="Close sponsor options">×</button>

        <div class="ff-sponsorModal__header">
          <span class="ff-eyebrow">Sponsor support</span>
          <h2 id="ff-sponsor-modal-title">Back the season with visible local support.</h2>
          <p>Choose a sponsor path. Recognition is reviewed before placement so the page stays clean, credible, and family-safe.</p>
        </div>

        <div class="ff-sponsorModal__grid" aria-label="Sponsor package options">
          <article class="ff-sponsorModal__card">
            <span>Community</span>
            <strong>$300</strong>
            <p>Local supporter recognition for families and small businesses.</p>
            <button class="ff-button ff-button--ghost ff-button--full" type="button" data-ff-sponsor-package="Community Partner">Choose Community</button>
          </article>

          <article class="ff-sponsorModal__card ff-sponsorModal__card--featured">
            <span>Featured</span>
            <strong>$750</strong>
            <p>Stronger placement for businesses helping cover real season costs.</p>
            <button class="ff-button ff-button--primary ff-button--full" type="button" data-ff-sponsor-package="Featured Sponsor">Choose Featured</button>
          </article>

          <article class="ff-sponsorModal__card">
            <span>Season</span>
            <strong>$1,500</strong>
            <p>Premier season support with top-tier campaign recognition.</p>
            <button class="ff-button ff-button--ghost ff-button--full" type="button" data-ff-sponsor-package="Season Sponsor">Choose Season</button>
          </article>
        </div>

        <div class="ff-sponsorModal__form" aria-label="Sponsor interest form">
          <label class="ff-formField">
            <span>Your name or business</span>
            <input type="text" name="sponsor_name" autocomplete="organization" placeholder="Business or family name">
          </label>

          <label class="ff-formField">
            <span>Email</span>
            <input type="email" name="sponsor_email" autocomplete="email" placeholder="you@example.com">
          </label>

          <label class="ff-formField">
            <span>Note</span>
            <input type="text" name="sponsor_note" placeholder="Tell the team how you want to help">
          </label>

          <button class="ff-button ff-button--primary ff-button--full" type="button" data-ff-sponsor-submit>
            Send sponsor interest
          </button>

          <p class="ff-sponsorModal__fineprint">Sponsor details can be confirmed by the organizer before anything appears publicly.</p>
        </div>
      </section>
    `;

    document.body.appendChild(node);
    return node;
  };

  const ensureModal = (name) => {
    if (name === "sponsor") return ensureSponsorModal();

    const config = REGISTRY[name];
    return config ? document.querySelector(config.modal) : null;
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const isElement = (value) => value instanceof Element;

  const lockPage = (name, rootClass) => {
    document.documentElement.classList.add("ff-modal-open", rootClass);
    document.documentElement.setAttribute("data-ff-modal-open", "true");
    document.documentElement.setAttribute(`data-${name}-open`, "true");

    if (document.body) {
      document.body.classList.add("ff-modal-open", rootClass);
      document.body.setAttribute("data-ff-modal-open", "true");
      document.body.setAttribute(`data-${name}-open`, "true");
    }
  };

  const unlockPage = (name, rootClass) => {
    document.documentElement.classList.remove(rootClass);
    document.documentElement.removeAttribute(`data-${name}-open`);

    if (document.body) {
      document.body.classList.remove(rootClass);
      document.body.removeAttribute(`data-${name}-open`);
    }

    const stillOpen = document.querySelector(
      "[data-ff-state='open'],.ff-is-open,#checkout[aria-hidden='false'],#qr-modal[aria-hidden='false'],#sponsor-modal[aria-hidden='false']"
    );

    if (!stillOpen) {
      document.documentElement.classList.remove("ff-modal-open");
      document.documentElement.removeAttribute("data-ff-modal-open");

      if (document.body) {
        document.body.classList.remove("ff-modal-open");
        document.body.removeAttribute("data-ff-modal-open");
      }
    }
  };

  const markOpen = (name) => {
    const config = REGISTRY[name];
    const node = ensureModal(name);
    if (!node) return;

    node.__ffEnterpriseSyncing = true;

    node.hidden = false;
    node.removeAttribute("hidden");
    node.setAttribute("aria-hidden", "false");
    node.setAttribute("data-ff-state", "open");
    node.setAttribute("data-ff-modal-state", "open");
    node.setAttribute(config.stateAttr, "open");
    node.classList.add("is-open", "ff-is-open");

    const panel = $(config.panel, node);
    if (panel) {
      if (!panel.hasAttribute("role")) panel.setAttribute("role", "dialog");
      panel.setAttribute("aria-modal", "true");
      if (!panel.hasAttribute("tabindex")) panel.setAttribute("tabindex", "-1");
    }

    lockPage(name, config.rootClass);

    window.requestAnimationFrame(() => {
      node.__ffEnterpriseSyncing = false;
    });
  };

  const markClosed = (name, force = true) => {
    const config = REGISTRY[name];
    const node = ensureModal(name);
    if (!node) return;

    node.__ffEnterpriseSyncing = true;

    node.setAttribute("aria-hidden", "true");
    node.setAttribute("data-ff-state", "closed");
    node.setAttribute("data-ff-modal-state", "closed");
    node.setAttribute(config.stateAttr, "closed");
    node.classList.remove("is-open", "ff-is-open");

    if (force) {
      node.hidden = true;
      node.setAttribute("hidden", "");
    }

    unlockPage(name, config.rootClass);

    window.requestAnimationFrame(() => {
      node.__ffEnterpriseSyncing = false;
    });
  };

  const openSoon = (name) => {
    [0, 16, 40, 90, 180, 320, 520].forEach((delay) => {
      window.setTimeout(() => markOpen(name), delay);
    });
  };

  const closeSoon = (name) => {
    [0, 80, 180].forEach((delay) => {
      window.setTimeout(() => markClosed(name, true), delay);
    });
  };

  const syncSelectedAmount = (trigger) => {
    if (!trigger) return;

    const raw =
      trigger.getAttribute("data-ff-checkout-amount") ||
      trigger.getAttribute("data-ff-amount") ||
      trigger.getAttribute("data-ff-donation-amount") ||
      trigger.textContent ||
      "";

    const amount = raw.replace(/[^0-9]/g, "");
    if (!amount) return;

    $$("[data-ff-checkout-amount],[data-ff-amount],[data-ff-donation-amount]").forEach((button) => {
      const value =
        button.getAttribute("data-ff-checkout-amount") ||
        button.getAttribute("data-ff-amount") ||
        button.getAttribute("data-ff-donation-amount") ||
        "";

      if (button.matches("button")) {
        const selected = value === amount;
        button.setAttribute("aria-pressed", selected ? "true" : "false");
        button.classList.toggle("is-selected", selected);
      }
    });

    $$("[data-ff-checkout-custom-input],[data-ff-custom-amount]").forEach((input) => {
      if (input instanceof HTMLInputElement) input.value = amount;
    });

    $$("[data-ff-checkout-payment-summary-amount]").forEach((node) => {
      node.textContent = `$${amount} donation`;
    });

    $$("[data-ff-start-embedded-checkout],[data-ff-donate-submit]").forEach((node) => {
      node.setAttribute("data-ff-checkout-amount", amount);
    });
  };

  const installClickBridge = () => {
    if (document.__ffEnterpriseContractClickBridge) return;
    document.__ffEnterpriseContractClickBridge = true;

    document.addEventListener(
      "click",
      (event) => {
        const target = isElement(event.target) ? event.target : null;
        if (!target) return;

        const amountTrigger = target.closest(
          "[data-ff-checkout-amount],[data-ff-amount],[data-ff-donation-amount]"
        );
        if (amountTrigger) syncSelectedAmount(amountTrigger);

        for (const [name, config] of Object.entries(REGISTRY)) {
          if (target.closest(config.open)) {
            openSoon(name);
            return;
          }

          if (target.closest(config.close)) {
            closeSoon(name);
            return;
          }
        }
      },
      true
    );

    document.addEventListener(
      "keydown",
      (event) => {
        if (event.key !== "Escape") return;
        Object.keys(REGISTRY).forEach((name) => markClosed(name, true));
      },
      true
    );
  };

  const installObservers = () => {
    Object.entries(REGISTRY).forEach(([name, config]) => {
      const node = $(config.modal);
      if (!node || node.__ffEnterpriseContractObserved) return;

      node.__ffEnterpriseContractObserved = true;

      const observer = new MutationObserver(() => {
        if (node.__ffEnterpriseSyncing) return;

        const externallyOpened =
          node.hidden === false &&
          node.getAttribute("hidden") === null &&
          node.getAttribute("aria-hidden") !== "true";

        if (
          externallyOpened ||
          node.classList.contains("is-open") ||
          node.classList.contains("ff-is-open")
        ) {
          markOpen(name);
        }
      });

      observer.observe(node, {
        attributes: true,
        attributeFilter: [
          "hidden",
          "aria-hidden",
          "class",
          "style",
          "data-ff-state",
          "data-ff-modal-state",
          config.stateAttr,
        ],
      });
    });
  };

  const boot = () => {
    installClickBridge();
    installObservers();
    document.documentElement.setAttribute("data-ff-enterprise-contract", "external-v1");
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }

  window.setTimeout(boot, 120);
  window.setTimeout(boot, 480);
})();

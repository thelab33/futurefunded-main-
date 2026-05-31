
/* FF_APP_STALE_ISLAND_BLOCKER_V3
   Prevents legacy homepage island script injection from requesting missing files.
   Active behavior is owned by ff-app.js and page-specific authority scripts.
*/
(() => {
  const staleIslandPattern = /\/static\/js\/islands\/(?:donate|share|sponsor|onboarding|faq)\.js(?:\?|$)/i;

  const isBlockedUrl = (value) => staleIslandPattern.test(String(value || ""));
  const isScript = (node) =>
    node && node.nodeType === 1 && String(node.tagName || "").toLowerCase() === "script";

  const markBlocked = (node) => {
    if (!isScript(node)) return false;
    node.setAttribute("data-ff-stale-island-blocked", "true");
    node.setAttribute("type", "application/x-futurefunded-blocked-island");
    node.removeAttribute("src");
    return true;
  };

  const shouldBlock = (node) =>
    isScript(node) && (isBlockedUrl(node.getAttribute("src")) || isBlockedUrl(node.src));

  const block = (node) => {
    if (!shouldBlock(node)) return false;
    return markBlocked(node);
  };

  const patchMethod = (proto, method) => {
    if (!proto || typeof proto[method] !== "function") return;
    const original = proto[method];
    const key = `__ffStaleIsland${method}PatchedV3`;
    if (original[key]) return;

    function patched(node, ...rest) {
      if (block(node)) return node;
      return original.call(this, node, ...rest);
    }

    patched[key] = true;
    proto[method] = patched;
  };

  patchMethod(Node.prototype, "appendChild");
  patchMethod(Node.prototype, "insertBefore");

  const originalSetAttribute = Element.prototype.setAttribute;
  if (typeof originalSetAttribute === "function" && !originalSetAttribute.__ffStaleIslandSetAttributePatchedV3) {
    function patchedSetAttribute(name, value, ...rest) {
      if (isScript(this) && String(name || "").toLowerCase() === "src" && isBlockedUrl(value)) {
        markBlocked(this);
        return undefined;
      }

      return originalSetAttribute.call(this, name, value, ...rest);
    }

    patchedSetAttribute.__ffStaleIslandSetAttributePatchedV3 = true;
    Element.prototype.setAttribute = patchedSetAttribute;
  }

  const srcDescriptor = Object.getOwnPropertyDescriptor(HTMLScriptElement.prototype, "src");
  if (srcDescriptor && typeof srcDescriptor.set === "function" && !srcDescriptor.set.__ffStaleIslandSrcSetterPatchedV3) {
    const originalSetter = srcDescriptor.set;
    const originalGetter = srcDescriptor.get;

    function patchedSrcSetter(value) {
      if (isBlockedUrl(value)) {
        markBlocked(this);
        return undefined;
      }

      return originalSetter.call(this, value);
    }

    patchedSrcSetter.__ffStaleIslandSrcSetterPatchedV3 = true;

    Object.defineProperty(HTMLScriptElement.prototype, "src", {
      configurable: true,
      enumerable: srcDescriptor.enumerable,
      get: originalGetter,
      set: patchedSrcSetter,
    });
  }
})();


/* eslint no-unused-vars: ["error", { "argsIgnorePattern": "^_", "varsIgnorePattern": "^_", "caughtErrors": "none" }], no-empty: ["error", { "allowEmptyCatch": true }] */
(() => {
  "use strict";

  const doc = document;
  const win = window;
  const root = doc.documentElement;
  const body = doc.body;

  function q(selector, scope = doc) {
    if (!selector) return null;
    try {
      return scope.querySelector(selector);
    } catch {
      return null;
    }
  }

  function qa(selector, scope = doc) {
    if (!selector) return [];
    try {
      return Array.from(scope.querySelectorAll(selector));
    } catch {
      return [];
    }
  }

  function parseJsonScript(id, fallback = {}) {
    const el = doc.getElementById(id);
    if (!el) return fallback;

    try {
      return JSON.parse(el.textContent || "{}");
    } catch (error) {
      console.warn(`[ff-app] failed to parse #${id}`, error);
      return fallback;
    }
  }

  function parseAmount(raw) {
    const clean = String(raw ?? "").replace(/[^\d.]/g, "");
    if (!clean) return 0;
    const value = Number(clean);
    return Number.isFinite(value) ? value : 0;
  }

  function money(value, currency = "USD") {
    const number = Number(value || 0);
    try {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
      }).format(Number.isFinite(number) ? number : 0);
    } catch {
      return `$${Math.round(Number.isFinite(number) ? number : 0).toLocaleString("en-US")}`;
    }
  }

  const config = parseJsonScript("ffConfig", {});
  const selectorPayload = parseJsonScript("ffSelectors", {});
  const payloadHooks =
    selectorPayload && typeof selectorPayload === "object" && selectorPayload.hooks
      ? selectorPayload.hooks
      : {};

  const defaults = {
    openCheckout: "[data-ff-open-checkout]",
    closeCheckout: "[data-ff-close-checkout]",
    checkoutSheet: "[data-ff-checkout-sheet]",
    checkoutViewport: "[data-ff-checkout-viewport]",
    checkoutContent: "[data-ff-checkout-content]",
    checkoutScroll: "[data-ff-checkout-scroll]",
    checkoutShell: "[data-ff-checkout-shell]",
    checkoutSuccess: "[data-ff-checkout-success]",
    checkoutError: "[data-ff-checkout-error]",
    checkoutStatus: "[data-ff-checkout-status]",
    donationForm: "#donationForm",
    amountInput: "[data-ff-amount-input]",
    amountChip: "[data-ff-amount]",
    donorName: "[data-ff-donor-name]",
    donorEmail: "[data-ff-email]",
    donorMessage: "[data-ff-message]",
    summaryAmount: "[data-ff-summary-amount]",
    teamId: "[data-ff-team-id]",
    paymentMount: "[data-ff-payment-element]",
    stripeMount: "[data-ff-stripe-mount]",
    paypalMount: "[data-ff-paypal-mount]",
    toasts: "[data-ff-toasts]",
    live: "[data-ff-live]",
    share: "[data-ff-share]",
    themeToggle: "[data-ff-theme-toggle]",
    openDrawer: "[data-ff-open-drawer]",
    closeDrawer: "[data-ff-close-drawer]",
    drawer: "[data-ff-drawer]",
    openSponsor: "[data-ff-open-sponsor]",
    closeSponsor: "[data-ff-close-sponsor]",
    sponsorModal: "[data-ff-sponsor-modal]",
    sponsorForm: "#sponsorForm",
    sponsorTier: "[data-ff-sponsor-tier]",
    sponsorTierGrid: "[data-ff-sponsor-tier-grid]",
    sponsorTierSelected: "[data-ff-sponsor-tier-selected]",
    sponsorTierCopy: "[data-ff-sponsor-tier-copy]",
    sponsorSubmit: "[data-ff-sponsor-submit]",
    sponsorStatus: "[data-ff-sponsor-status]",
    sponsorError: "[data-ff-sponsor-error]",
    sponsorSuccess: "[data-ff-sponsor-success]",
    openVideo: "[data-ff-open-video]",
    closeVideo: "[data-ff-close-video]",
    videoModal: "[data-ff-video-modal]",
    videoFrame: "[data-ff-video-frame]",
    videoMount: "[data-ff-video-mount]",
    videoPanel: "[data-ff-video-panel]",
    videoStatus: "[data-ff-video-status]",
    openTerms: "[data-ff-open-terms]",
    closeTerms: "[data-ff-close-terms]",
    termsModal: "[data-ff-terms-modal]",
    openPrivacy: "[data-ff-open-privacy]",
    closePrivacy: "[data-ff-close-privacy]",
    privacyModal: "[data-ff-privacy-modal]",
    openOnboard: "[data-ff-open-onboard]",
    closeOnboard: "[data-ff-close-onboard]",
    onboardModal: "[data-ff-onboard-modal]",
    onboardForm: "[data-ff-onboard-form]",
    onboardNext: "[data-ff-onboard-next]",
    onboardPrev: "[data-ff-onboard-prev]",
    onboardFinish: "[data-ff-onboard-finish]",
    onboardSummary: "[data-ff-onboard-summary]",
    onboardStatus: "[data-ff-onboard-status]",
    onboardResult: "[data-ff-onboard-result]",
    onboardEmail: "[data-ff-onboard-email]",
    onboardCopy: "[data-ff-onboard-copy]",
    stepPill: "[data-ff-step-pill]",
    stepPanel: "[data-ff-step]",
    floatingDonate: "[data-ff-floating-donate]",
    backToTop: "[data-ff-backtotop]",
    tabs: "[data-ff-tabs]",
    story: "[data-ff-story]",
  };

  const selectors = { ...defaults, ...payloadHooks };

  const state = {
    activeOverlay: null,
    lastTrigger: null,
    restoreThemeKey: "ff-theme",
    apiBaseUrl: null,
    paymentConfig: null,
    islandsReady: false,
  };

  function announce(message) {
    const live = q(selectors.live);
    if (!live) return;
    live.textContent = "";
    win.requestAnimationFrame(() => {
      live.textContent = message;
    });
  }

  function toast(message, tone = "success") {
    const host = q(selectors.toasts);
    if (!host) return;

    const item = doc.createElement("div");
    item.className = `ff-toast ff-toast--${tone}`;
    item.setAttribute("role", "status");
    item.textContent = message;

    host.appendChild(item);

    win.setTimeout(() => {
      item.classList.add("ff-reveal-prep");
      item.classList.add("ff-reveal-prep");
      win.setTimeout(() => item.remove(), 220);
    }, 3200);
  }

  function getFocusable(container) {
    return qa(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      container
    ).filter((el) => el.offsetParent !== null || el === doc.activeElement);
  }

  function isMeaningfulInput(el) {
    if (!(el instanceof Element)) return false;

    const tag = (el.tagName || "").toUpperCase();
    if (tag === "TEXTAREA" || tag === "SELECT") return true;
    if (tag !== "INPUT") return false;

    const type = (el.getAttribute("type") || "text").toLowerCase();
    return !["hidden", "button", "submit", "reset", "checkbox", "radio"].includes(type);
  }

  function preferredOverlayFocusTarget(overlay) {
    const sponsorModal = q(selectors.sponsorModal);
    const checkoutSheet = q(selectors.checkoutSheet);
    const onboardModal = q(selectors.onboardModal);

    if (sponsorModal && overlay === sponsorModal) {
      return (
        q('input[name="business_name"]', overlay) ||
        q('input[name="contact_name"]', overlay) ||
        q('input[name="contact_email"]', overlay) ||
        getFocusable(overlay).find(isMeaningfulInput) ||
        getFocusable(overlay)[0] ||
        null
      );
    }

    if (checkoutSheet && overlay === checkoutSheet) {
      return (
        q(selectors.amountInput, overlay) ||
        q('input[name="donor_name"]', overlay) ||
        q('input[name="donor_email"]', overlay) ||
        getFocusable(overlay).find(isMeaningfulInput) ||
        getFocusable(overlay)[0] ||
        null
      );
    }

    if (onboardModal && overlay === onboardModal) {
      return (
        q('input[name="organization_name"]', overlay) ||
        q(selectors.onboardEmail, overlay) ||
        getFocusable(overlay).find(isMeaningfulInput) ||
        getFocusable(overlay)[0] ||
        null
      );
    }

    const focusable = getFocusable(overlay);
    return (
      focusable.find((el) => el.hasAttribute("autofocus")) ||
      focusable.find(isMeaningfulInput) ||
      focusable[0] ||
      null
    );
  }

  function setExpandedForSelector(selector, expanded) {
    qa(selector).forEach((node) => {
      node.setAttribute("aria-expanded", String(expanded));
    });
  }

  function syncOverlayToggleState(overlay, open) {
    const drawer = q(selectors.drawer);
    const checkout = q(selectors.checkoutSheet);
    const sponsor = q(selectors.sponsorModal);
    const terms = q(selectors.termsModal);
    const privacy = q(selectors.privacyModal);
    const onboard = q(selectors.onboardModal);
    const video = q(selectors.videoModal);

    if (drawer && overlay === drawer) setExpandedForSelector(selectors.openDrawer, open);
    if (checkout && overlay === checkout) setExpandedForSelector(selectors.openCheckout, open);
    if (sponsor && overlay === sponsor) setExpandedForSelector(selectors.openSponsor, open);
    if (terms && overlay === terms) setExpandedForSelector(selectors.openTerms, open);
    if (privacy && overlay === privacy) setExpandedForSelector(selectors.openPrivacy, open);
    if (onboard && overlay === onboard) setExpandedForSelector(selectors.openOnboard, open);
    if (video && overlay === video) setExpandedForSelector(selectors.openVideo, open);
  }


  function setOverlayLifecycleState(overlay, open) {
    if (!overlay) return;

    overlay.hidden = !open;
    overlay.setAttribute("aria-hidden", open ? "false" : "true");

    if (open) {
      overlay.dataset.open = "true";
      overlay.dataset.ffState = "open";
      overlay.dataset.ffModalState = "open";
      overlay.dataset.ffCheckoutState = "open";
      overlay.classList.add("is-open", "ff-is-open");
      return;
    }

    delete overlay.dataset.open;
    overlay.dataset.ffState = "closed";
    overlay.dataset.ffModalState = "closed";
    overlay.dataset.ffCheckoutState = "closed";
    overlay.classList.remove("is-open", "ff-is-open");
  }

  function openOverlay(overlay, trigger = null) {
    if (!overlay) return;

    if (state.activeOverlay && state.activeOverlay !== overlay) {
      closeOverlay(state.activeOverlay, false);
    }

    state.activeOverlay = overlay;
    state.lastTrigger = trigger || doc.activeElement || null;

    setOverlayLifecycleState(overlay, true);
    syncOverlayToggleState(overlay, true);

    if (body) {
      body.classList.add("ff-scroll-lock");
      body.dataset.ffOverlayOpen = "true";
    }

    const target = preferredOverlayFocusTarget(overlay);
    if (target) {
      win.requestAnimationFrame(() => target.focus());
    }
  }

  function normalizeVideoSrc(raw) {
    const src = String(raw || "").trim();
    if (!src) return "";

    try {
      const url = new URL(src, win.location.origin);
      const host = url.hostname.replace(/^www\./, "");

      if (host in { "youtube.com": 1, "m.youtube.com": 1 }) {
        if (url.pathname === "/watch" && url.searchParams.get("v")) {
          return `https://www.youtube.com/embed/${url.searchParams.get("v")}`;
        }
        if (url.pathname.startsWith("/embed/")) {
          return url.toString();
        }
      }

      if (host === "youtu.be") {
        const id = url.pathname.replace(/^\//, "");
        if (id) return `https://www.youtube.com/embed/${id}`;
      }

      if (host === "vimeo.com") {
        const id = url.pathname.replace(/^\//, "");
        if (/^\d+$/.test(id)) {
          return `https://player.vimeo.com/video/${id}`;
        }
      }

      return url.toString();
    } catch {
      return src;
    }
  }

  function videoNodes(scope = doc) {
    return {
      modal: q(selectors.videoModal, scope) || q(selectors.videoModal),
      panel: q(selectors.videoPanel, scope) || q(selectors.videoPanel),
      frame: q(selectors.videoFrame, scope) || q(selectors.videoFrame),
      mount: q(selectors.videoMount, scope) || q(selectors.videoMount),
      status: q(selectors.videoStatus, scope) || q(selectors.videoStatus),
    };
  }

  function renderVideoSource(raw) {
    const { mount, frame, status } = videoNodes();
    const host = mount || frame;
    const src = normalizeVideoSrc(raw);

    if (!host) return false;

    host.innerHTML = "";

    if (!src) {
      if (status) status.textContent = "Video unavailable right now.";
      return false;
    }

    const iframe = doc.createElement("iframe");
    iframe.src = src;
    iframe.title = "Campaign story video";
    iframe.loading = "lazy";
    iframe.allow =
      "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.setAttribute("frameborder", "0");
    iframe.classList.add("ff-embed-frame");

    host.appendChild(iframe);

    if (status) status.textContent = "Story video loaded.";
    return true;
  }

  function resetOverlayMedia(overlay) {
    const { modal, mount, frame, status } = videoNodes(overlay || doc);
    if (modal && overlay === modal) {
      if (mount) mount.innerHTML = "";
      else if (frame) frame.innerHTML = "";
      if (status) status.textContent = "The story video will load here when opened.";
    }
  }

  function closeOverlay(overlay, restoreFocus = true) {
    if (!overlay) return;

    resetOverlayMedia(overlay);

    setOverlayLifecycleState(overlay, false);
    syncOverlayToggleState(overlay, false);

    if (state.activeOverlay === overlay) {
      state.activeOverlay = null;
      if (body) {
        body.classList.remove("ff-scroll-lock");
        delete body.dataset.ffOverlayOpen;
      }
    }

    if (restoreFocus && state.lastTrigger && typeof state.lastTrigger.focus === "function") {
      win.requestAnimationFrame(() => state.lastTrigger.focus());
    }
  }

  function shouldAllowNativeNavigation(node) {
    if (!(node instanceof Element)) return false;
    if (node.tagName !== "A") return false;

    const href = (node.getAttribute("href") || "").trim();
    if (!href) return false;
    if (href === "#") return false;
    if (href.toLowerCase().startsWith("javascript:")) return false;
    return true;
  }

  function bindOverlay(openSel, closeSel, overlaySel) {
    const overlay = q(overlaySel);
    if (!overlay) return;

    qa(openSel).forEach((trigger) => {
      if (trigger.dataset.ffOpenBound === "true") return;
      trigger.dataset.ffOpenBound = "true";

      trigger.addEventListener("click", (event) => {
        event.preventDefault();
        openOverlay(overlay, trigger);
      });
    });

    const explicitClosers = qa(
      `button${closeSel}, a${closeSel}, [role="button"]${closeSel}, [data-ff-close]`,
      overlay
    );

    explicitClosers.forEach((node) => {
      if (node.dataset.ffCloseBound === "true") return;
      node.dataset.ffCloseBound = "true";

      node.addEventListener("click", (event) => {
        const allowNavigation = shouldAllowNativeNavigation(node);
        if (!allowNavigation) {
          event.preventDefault();
        }
        closeOverlay(overlay, !allowNavigation);
      });
    });

    const backdrop = q(".ff-sheet__backdrop, .ff-modal__backdrop", overlay);
    if (backdrop && backdrop.dataset.ffBackdropBound !== "true") {
      backdrop.dataset.ffBackdropBound = "true";
      backdrop.addEventListener("click", (event) => {
        event.preventDefault();
        closeOverlay(overlay);
      });
    }
  }

  function bindEscapeClose() {
    doc.addEventListener("keydown", (event) => {
      if (state.activeOverlay && event.key === "Tab") {
        const focusable = getFocusable(state.activeOverlay);

        if (!focusable.length) {
          event.preventDefault();
          return;
        }

        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const active = doc.activeElement;

        if (event.shiftKey) {
          if (active === first || !state.activeOverlay.contains(active)) {
            event.preventDefault();
            last.focus();
          }
        } else if (active === last) {
          event.preventDefault();
          first.focus();
        }
      }

      if (event.key === "Escape" && state.activeOverlay) {
        closeOverlay(state.activeOverlay);
      }
    });
  }

  function bindThemeToggle() {
    const saved = win.localStorage.getItem(state.restoreThemeKey);
    if (saved === "light" || saved === "dark") {
      root.setAttribute("data-theme", saved);
      if (body) body.setAttribute("data-theme", saved);
    }

    qa(selectors.themeToggle).forEach((button) => {
      if (button.dataset.ffThemeBound === "true") return;
      button.dataset.ffThemeBound = "true";

      button.addEventListener("click", (event) => {
        event.preventDefault();

        const current =
          root.getAttribute("data-theme") || body?.getAttribute("data-theme") || "dark";
        const next = current === "light" ? "dark" : "light";

        root.setAttribute("data-theme", next);
        if (body) body.setAttribute("data-theme", next);
        win.localStorage.setItem(state.restoreThemeKey, next);
        announce(`Theme changed to ${next}.`);
      });
    });
  }

  function bindBackToTop() {
    qa(selectors.backToTop).forEach((button) => {
      if (button.dataset.ffBackTopBound === "true") return;
      button.dataset.ffBackTopBound = "true";

      button.addEventListener("click", (event) => {
        event.preventDefault();
        win.scrollTo({ top: 0, behavior: "smooth" });
      });
    });
  }

  function bindFloatingDonate() {
    const triggers = qa(selectors.floatingDonate);
    if (!triggers.length) return;

    const sheet = q(selectors.checkoutSheet);
    triggers.forEach((button) => {
      if (button.dataset.ffFloatingBound === "true") return;
      button.dataset.ffFloatingBound = "true";

      button.addEventListener("click", (event) => {
        event.preventDefault();
        if (sheet) {
          openOverlay(sheet, button);
          return;
        }

        const donateTarget = doc.getElementById("checkout") || doc.getElementById("donate");
        if (donateTarget) {
          donateTarget.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
  }

  function bindVideoModal() {
    const { modal, mount, frame, status } = videoNodes();

    if (!modal || (!mount && !frame)) return;

    qa(selectors.openVideo).forEach((trigger) => {
      if (trigger.dataset.ffVideoOpenBound === "true") return;
      trigger.dataset.ffVideoOpenBound = "true";

      trigger.addEventListener("click", (event) => {
        event.preventDefault();

        const src =
          trigger.getAttribute("data-video-src") ||
          trigger.getAttribute("data-ff-video-src") ||
          mount?.getAttribute("data-video-src") ||
          frame?.getAttribute("data-video-src") ||
          mount?.dataset?.videoSrc ||
          frame?.dataset?.videoSrc ||
          "";

        renderVideoSource(src);
        if (status && src) status.textContent = "Opening story video...";
        openOverlay(modal, trigger);
      });
    });

    qa(`button${selectors.closeVideo}, a${selectors.closeVideo}`, modal).forEach((button) => {
      if (button.dataset.ffVideoCloseBound === "true") return;
      button.dataset.ffVideoCloseBound = "true";

      button.addEventListener("click", (event) => {
        event.preventDefault();
        closeOverlay(modal);
      });
    });

    const backdrop = q(".ff-sheet__backdrop, .ff-modal__backdrop", modal);
    if (backdrop && backdrop.dataset.ffVideoBackdropBound !== "true") {
      backdrop.dataset.ffVideoBackdropBound = "true";
      backdrop.addEventListener("click", (event) => {
        event.preventDefault();
        closeOverlay(modal);
      });
    }
  }

  function setNodeMessage(node, message, tone = "success") {
    if (!node) return;
    node.hidden = false;
    node.textContent = message;
    node.dataset.tone = tone;
  }

  function clearNodeMessage(node) {
    if (!node) return;
    node.hidden = true;
    node.textContent = "";
    delete node.dataset.tone;
  }

  function clearMessageGroup(...nodes) {
    nodes.forEach(clearNodeMessage);
  }

  function formSubmitButton(form) {
    if (!form) return null;
    return q('button[type="submit"], input[type="submit"]', form);
  }

  function setButtonBusy(button, busy, label = "Working...") {
    if (!button) return;

    const tag = (button.tagName || "").toUpperCase();
    const isInput = tag === "INPUT";

    if (busy) {
      if (!button.dataset.ffOriginalLabel) {
        button.dataset.ffOriginalLabel = isInput ? button.value || "" : button.textContent || "";
      }

      button.disabled = true;
      button.setAttribute("aria-busy", "true");

      if (isInput) {
        button.value = label;
      } else {
        button.textContent = label;
      }

      return;
    }

    button.disabled = false;
    button.removeAttribute("aria-busy");

    if (button.dataset.ffOriginalLabel) {
      if (isInput) {
        button.value = button.dataset.ffOriginalLabel;
      } else {
        button.textContent = button.dataset.ffOriginalLabel;
      }
      delete button.dataset.ffOriginalLabel;
    }
  }

  function resolveCurrentScript() {
    if (doc.currentScript && doc.currentScript.src) {
      return doc.currentScript;
    }

    return (
      Array.from(doc.scripts).find((script) =>
        (script.src || "").includes("/static/js/ff-app.js")
      ) || null
    );
  }

  function resolveStaticJsBase() {
    const script = resolveCurrentScript();
    const src = script?.src || "";
    const clean = src.split("?")[0];

    if (clean.includes("/static/js/ff-app.js")) {
      return clean.replace(/\/ff-app\.js$/, "");
    }

    return "/static/js";
  }

  function resolveApiBaseUrl() {
    if (state.apiBaseUrl) return state.apiBaseUrl;

    const fromConfig =
      config.apiBaseUrl ||
      config.api_base_url ||
      config.API_BASE_URL ||
      body?.dataset?.ffApiBaseUrl ||
      "";

    if (fromConfig) {
      state.apiBaseUrl = String(fromConfig).replace(/\/+$/, "");
      return state.apiBaseUrl;
    }

    if (win.location.port === "5000") {
      state.apiBaseUrl = `${win.location.protocol}//${win.location.hostname}:8000`;
      return state.apiBaseUrl;
    }

    state.apiBaseUrl = win.location.origin.replace(/\/+$/, "");
    return state.apiBaseUrl;
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    const text = await response.text();
    let data = null;

    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { ok: false, raw: text };
    }

    if (!response.ok) {
      const message =
        data?.message || data?.error || `Request failed with status ${response.status}`;
      const error = new Error(message);
      error.response = response;
      error.data = data;
      throw error;
    }

    return data;
  }

  function currentCampaignSlug() {
    return (
      config.campaignSlug ||
      config.campaign_slug ||
      body?.dataset?.ffCampaignSlug ||
      (() => {
        const parts = win.location.pathname.split("/").filter(Boolean);
        const idx = parts.indexOf("c");
        return idx >= 0 ? parts[idx + 1] || "campaign" : "campaign";
      })()
    );
  }

  async function getPaymentConfig() {
    if (state.paymentConfig) return state.paymentConfig;
    const apiBase = resolveApiBaseUrl();
    state.paymentConfig = await fetchJson(`${apiBase}/payments/config`, {
      method: "GET",
      headers: {},
    });
    return state.paymentConfig;
  }

  function donationScope() {
    return q(selectors.checkoutSheet) || q(selectors.donationForm) || doc;
  }

  function donationPayload() {
    const scope = donationScope();
    const amountInput = q(selectors.amountInput, scope);
    const donorName = q(selectors.donorName, scope);
    const donorEmail = q(selectors.donorEmail, scope);
    const donorMessage = q(selectors.donorMessage, scope);
    const teamId = q(selectors.teamId, scope);

    return {
      campaign_slug: currentCampaignSlug(),
      amount: parseAmount(amountInput?.value || ""),
      currency: config.currency || config.CURRENCY || "USD",
      donor_name: donorName?.value?.trim() || "",
      donor_email: donorEmail?.value?.trim() || "",
      donor_message: donorMessage?.value?.trim() || "",
      team_id: teamId?.value?.trim() || "",
      checkout_kind: "donation",
    };
  }

  function sponsorPayload(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  function onboardingPayload(form) {
    const raw = Object.fromEntries(new FormData(form).entries());
    const goal = parseAmount(raw.goal || 0);
    return { ...raw, goal };
  }

  function ensureFallbackAmountBinding() {
    const scope = donationScope();
    const amountInput = q(selectors.amountInput, scope);
    const chips = qa(selectors.amountChip, scope).length
      ? qa(selectors.amountChip, scope)
      : qa(selectors.amountChip);

    chips.forEach((chip) => {
      if (chip.dataset.ffAmountBound === "true") return;
      chip.dataset.ffAmountBound = "true";

      chip.addEventListener("click", (event) => {
        event.preventDefault();

        const value = chip.getAttribute("data-ff-amount") || chip.dataset.ffAmount || "";
        const amount = parseAmount(value);

        if (amountInput) {
          amountInput.value = amount ? String(amount) : "";
          amountInput.dispatchEvent(new Event("input", { bubbles: true }));
        }

        qa(selectors.summaryAmount).forEach((node) => {
          node.textContent = money(amount, config.currency || "USD");
        });

        chips.forEach((node) => {
          const nodeAmount = parseAmount(
            node.getAttribute("data-ff-amount") || node.dataset.ffAmount || ""
          );
          node.setAttribute("aria-pressed", String(nodeAmount === amount && amount > 0));
        });
      });
    });

    if (amountInput && amountInput.dataset.ffAmountInputBound !== "true") {
      amountInput.dataset.ffAmountInputBound = "true";
      amountInput.addEventListener("input", () => {
        const amount = parseAmount(amountInput.value);
        qa(selectors.summaryAmount).forEach((node) => {
          node.textContent = money(amount, config.currency || "USD");
        });
      });
    }
  }

  function ensureFallbackShareBinding() {
    qa(selectors.share).forEach((button) => {
      if (button.dataset.ffShareBound === "true") return;
      button.dataset.ffShareBound = "true";

      button.addEventListener("click", async (event) => {
        event.preventDefault();

        const url =
          button.getAttribute("data-share-url") ||
          body?.getAttribute("data-ff-share-url") ||
          config.shareUrl ||
          win.location.href;

        const title = doc.title || config.pageTitle || "FutureFunded Campaign";
        const text = button.getAttribute("data-share-text") || "Support this campaign.";

        try {
          if (navigator.share) {
            await navigator.share({ title, text, url });
            announce("Share sheet opened.");
            return;
          }

          if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(url);
            toast("Campaign link copied.");
            announce("Campaign link copied.");
            return;
          }

          win.prompt("Copy this link:", url);
        } catch (error) {
          console.warn("[ff-app] share failed", error);
          toast("Could not complete share action.", "warning");
        }
      });
    });
  }

  function ensureFallbackTabsBinding() {
    qa(selectors.tabs).forEach((tabsRoot) => {
      if (tabsRoot.dataset.ffTabsBound === "true") return;
      tabsRoot.dataset.ffTabsBound = "true";

      const triggers = qa("[data-ff-tab]", tabsRoot);
      const panels = qa("[data-ff-panel]", tabsRoot);

      if (!triggers.length || !panels.length) return;

      function activate(id) {
        triggers.forEach((button) => {
          const active = button.getAttribute("data-ff-tab") === id;
          button.setAttribute("aria-selected", String(active));
          button.setAttribute("tabindex", active ? "0" : "-1");
        });

        panels.forEach((panel) => {
          const active = panel.getAttribute("data-ff-panel") === id;
          panel.hidden = !active;
        });
      }

      triggers.forEach((button) => {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          activate(button.getAttribute("data-ff-tab"));
        });
      });

      activate(triggers[0].getAttribute("data-ff-tab"));
    });
  }

  function sponsorTierOpenButtons() {
    return qa(selectors.openSponsor).filter((node) => {
      return (
        node.hasAttribute("data-tier") ||
        node.hasAttribute("data-tier-id") ||
        node.hasAttribute("data-ff-sponsor-tier")
      );
    });
  }

  function sponsorTierButtons() {
    return [...qa(selectors.sponsorTier), ...sponsorTierOpenButtons()];
  }

  function sponsorTierStateFromNode(node) {
    return {
      value: (
        node.getAttribute("data-tier") ||
        node.getAttribute("data-ff-sponsor-tier") ||
        node.dataset.tier ||
        node.dataset.ffSponsorTier ||
        node.value ||
        ""
      ).trim(),
      tierId: (node.getAttribute("data-tier-id") || node.dataset.tierId || "").trim(),
    };
  }

  function sponsorTierInputs() {
    return qa(
      'input[name="sponsor_tier"], input[data-ff-sponsor-tier-value], input[data-ff-sponsor-tier-selected]'
    );
  }

  function writeSponsorTierState(value = "", tierId = "") {
    const cleanValue = String(value || "").trim();
    const cleanTierId = String(tierId || "").trim();
    const defaultCopy =
      "Choose a sponsor package from the cards above, or send a general sponsor inquiry.";

    sponsorTierInputs().forEach((input) => {
      if ("value" in input) {
        input.value = cleanValue;
      }
      if (cleanTierId) {
        input.dataset.selectedTierId = cleanTierId;
      } else {
        delete input.dataset.selectedTierId;
      }
    });

    qa(selectors.sponsorTierSelected).forEach((node) => {
      const tag = (node.tagName || "").toUpperCase();
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        node.value = cleanValue;
        if (cleanTierId) {
          node.dataset.selectedTierId = cleanTierId;
        } else {
          delete node.dataset.selectedTierId;
        }
        return;
      }

      node.textContent = cleanValue ? `Selected: ${cleanValue}` : "No package selected yet.";
    });

    qa(selectors.sponsorTierCopy).forEach((node) => {
      node.textContent = cleanValue
        ? `${cleanValue} selected. You can send this package as-is or adjust your message before submitting.`
        : defaultCopy;
    });

    sponsorTierButtons().forEach((node) => {
      const { value: nodeValue, tierId: nodeTierId } = sponsorTierStateFromNode(node);
      const active =
        (cleanTierId && nodeTierId && cleanTierId === nodeTierId) ||
        (!!cleanValue && cleanValue === nodeValue);

      node.dataset.selected = String(active);

      if ((node.tagName || "").toUpperCase() === "BUTTON") {
        node.setAttribute("aria-pressed", String(active));
      }
    });
  }

  function ensureFallbackSponsorTierBinding(resetOnly = false) {
    if (resetOnly) {
      writeSponsorTierState("", "");
      return;
    }

    sponsorTierButtons().forEach((button) => {
      if (button.dataset.ffSponsorBound === "true") return;
      button.dataset.ffSponsorBound = "true";

      button.addEventListener("click", () => {
        const { value, tierId } = sponsorTierStateFromNode(button);
        if (!value) return;
        writeSponsorTierState(value, tierId);
      });
    });

    const seeded = sponsorTierInputs().find((input) => String(input.value || "").trim());
    if (seeded) {
      writeSponsorTierState(seeded.value, seeded.dataset?.selectedTierId || "");
    } else {
      writeSponsorTierState("", "");
    }
  }

  function bindSponsorModalExperience() {
    const modal = q(selectors.sponsorModal);
    if (!modal || modal.dataset.ffSponsorExperienceBound === "true") return;

    modal.dataset.ffSponsorExperienceBound = "true";

    qa(selectors.openSponsor).forEach((trigger) => {
      if (trigger.dataset.ffSponsorOpenBound === "true") return;
      trigger.dataset.ffSponsorOpenBound = "true";

      trigger.addEventListener("click", () => {
        const { value, tierId } = sponsorTierStateFromNode(trigger);

        if (value) {
          writeSponsorTierState(value, tierId);
          return;
        }

        const seeded = sponsorTierInputs().find((input) => String(input.value || "").trim());
        if (seeded) {
          writeSponsorTierState(seeded.value, seeded.dataset?.selectedTierId || "");
        }
      });
    });
  }

  async function loadIsland(name) {
    win.FutureFundedIslands = win.FutureFundedIslands || {};

    if (typeof win.FutureFundedIslands[name] === "function") {
      return true;
    }

    const base = resolveStaticJsBase();
    const version = config.assetVersion || config.asset_v || config.ASSET_V || "";
    const src = `${base}/islands/${name}.js${version ? `?v=${encodeURIComponent(version)}` : ""}`;

    return new Promise((resolve) => {
      const existing = Array.from(doc.scripts).find(
        (script) => script.src && script.src.includes(`/islands/${name}.js`)
      );

      if (existing) {
        existing.addEventListener("load", () => resolve(true), { once: true });
        existing.addEventListener("error", () => resolve(false), { once: true });
        return;
      }

      const script = doc.createElement("script");
      script.src = src;
      script.defer = true;
      script.onload = () => resolve(true);
      script.onerror = () => {
        console.warn(`[ff-app] failed to load island: ${name}`);
        resolve(false);
      };
      doc.head.appendChild(script);
    });
  }

  async function bootIslands(app) {
    const names = ["donate", "sponsor", "onboarding", "faq", "share"];
    await Promise.all(names.map((name) => loadIsland(name)));

    win.FutureFundedIslands = win.FutureFundedIslands || {};
    app.islands = app.islands || {};

    names.forEach((name) => {
      const init = win.FutureFundedIslands[name];
      if (typeof init === "function" && !app.islands[name]) {
        try {
          app.islands[name] = init(app);
        } catch (error) {
          console.warn(`[ff-app] island boot failed: ${name}`, error);
        }
      }
    });

    if (!app.islands.donate) ensureFallbackAmountBinding();
    if (!app.islands.share) ensureFallbackShareBinding();
    if (!app.islands.faq) ensureFallbackTabsBinding();
    ensureFallbackSponsorTierBinding();

    state.islandsReady = true;
  }

  function bindDonationRuntime(app) {
    const form = q(selectors.donationForm);
    if (!form || form.dataset.ffRuntimeBound === "true") return;

    form.dataset.ffRuntimeBound = "true";

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const statusNode = q(selectors.checkoutStatus);
      const errorNode = q(selectors.checkoutError);
      const successNode = q(selectors.checkoutSuccess);
      const stripeMount = q(selectors.stripeMount);
      const paypalMount = q(selectors.paypalMount);
      const submitButton = formSubmitButton(form);

      clearMessageGroup(statusNode, errorNode, successNode);

      if (
        app.islands?.donate?.validateBeforeCheckout &&
        !app.islands.donate.validateBeforeCheckout()
      ) {
        return;
      }

      const payload = donationPayload();
      if (!payload.amount || payload.amount <= 0) {
        setNodeMessage(errorNode, "Choose a valid donation amount to continue.", "warning");
        return;
      }

      setNodeMessage(statusNode, "Preparing your secure checkout...", "info");
      setButtonBusy(submitButton, true, "Preparing...");

      try {
        const configResponse = await getPaymentConfig();
        const providers = configResponse?.providers || {};
        let response = null;

        if (providers.stripe?.enabled) {
          response = await fetchJson(`${resolveApiBaseUrl()}/payments/stripe/intent`, {
            method: "POST",
            body: JSON.stringify(payload),
          });

          if (stripeMount) {
            stripeMount.textContent = response.client_secret
              ? "Stripe intent created. Ready for secure payment mount."
              : "Stripe response received.";
          }
        } else if (providers.paypal?.enabled) {
          response = await fetchJson(`${resolveApiBaseUrl()}/payments/paypal/order`, {
            method: "POST",
            body: JSON.stringify(payload),
          });

          if (paypalMount) {
            paypalMount.textContent = response.order_id
              ? "PayPal order created. Ready for approval flow."
              : "PayPal response received.";
          }
        } else {
          throw new Error("Payments are not configured yet.");
        }

        clearNodeMessage(statusNode);
        setNodeMessage(
          successNode,
          response.provider === "paypal"
            ? "PayPal checkout is ready. Continue with the secure approval flow."
            : "Your secure checkout is ready. Continue with payment below.",
          "success"
        );

        toast("Checkout is ready.", "success");
        announce("Secure checkout is ready.");
        doc.dispatchEvent(new CustomEvent("ff:checkout:ready", { detail: response }));
      } catch (error) {
        console.warn("[ff-app] donation submit failed", error);
        clearNodeMessage(statusNode);
        setNodeMessage(
          errorNode,
          error?.data?.message ||
            error.message ||
            "We could not prepare checkout right now. Please try again.",
          "warning"
        );
        toast("We could not prepare checkout right now.", "warning");
      } finally {
        setButtonBusy(submitButton, false);
      }
    });
  }

  function bindSponsorRuntime(app) {
    const form = q(selectors.sponsorForm);
    if (!form || form.dataset.ffRuntimeSubmitBound === "true") return;

    form.dataset.ffRuntimeSubmitBound = "true";

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const statusNode = q(selectors.sponsorStatus);
      const errorNode = q(selectors.sponsorError);
      const successNode = q(selectors.sponsorSuccess);
      const submitButton = formSubmitButton(form);

      clearMessageGroup(statusNode, errorNode, successNode);

      if (app.islands?.sponsor?.validateSponsorForm && !app.islands.sponsor.validateSponsorForm()) {
        return;
      }

      setNodeMessage(statusNode, "Sending sponsor details...", "info");
      setButtonBusy(submitButton, true, "Sending...");

      try {
        const response = await fetchJson(`${resolveApiBaseUrl()}/sponsors/lead`, {
          method: "POST",
          body: JSON.stringify(sponsorPayload(form)),
        });

        clearNodeMessage(statusNode);

        if (app.islands?.sponsor?.setSubmitted) {
          app.islands.sponsor.setSubmitted(
            response.message || "Sponsor interest sent. We will follow up with the next steps."
          );
        } else {
          setNodeMessage(
            successNode,
            response.message || "Sponsor interest sent. We will follow up with the next steps.",
            "success"
          );
        }

        form.reset();
        ensureFallbackSponsorTierBinding(true);
        toast("Sponsor interest sent.", "success");
        announce("Sponsor interest sent.");
        doc.dispatchEvent(new CustomEvent("ff:sponsor:submitted", { detail: response }));
      } catch (error) {
        console.warn("[ff-app] sponsor submit failed", error);
        clearNodeMessage(statusNode);

        if (app.islands?.sponsor?.setFailed) {
          app.islands.sponsor.setFailed(
            error?.data?.message ||
              error.message ||
              "We could not send sponsor interest right now. Please try again."
          );
        } else {
          setNodeMessage(
            errorNode,
            error?.data?.message ||
              error.message ||
              "We could not send sponsor interest right now. Please try again.",
            "warning"
          );
        }

        toast("We could not send sponsor interest right now.", "warning");
      } finally {
        setButtonBusy(submitButton, false);
      }
    });
  }

  function bindOnboardingRuntime(_app) {
    const form = q(selectors.onboardForm);
    if (!form || form.dataset.ffRuntimeSubmitBound === "true") return;

    form.dataset.ffRuntimeSubmitBound = "true";

    const finishButtons = qa(selectors.onboardFinish);

    async function submitOnboarding(event) {
      if (event) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }

      const statusNode = q(selectors.onboardStatus);
      const resultNode = q(selectors.onboardResult);
      const submitButton =
        event &&
        event.currentTarget &&
        typeof event.currentTarget.matches === "function" &&
        event.currentTarget.matches("button, input")
          ? event.currentTarget
          : finishButtons.find((button) => !button.hidden) || formSubmitButton(form);

      clearMessageGroup(statusNode, resultNode);
      setNodeMessage(statusNode, "Saving your launch setup...", "info");
      setButtonBusy(submitButton, true, "Saving...");

      try {
        const response = await fetchJson(`${resolveApiBaseUrl()}/onboarding/save`, {
          method: "POST",
          body: JSON.stringify(onboardingPayload(form)),
        });

        clearNodeMessage(statusNode);
        setNodeMessage(
          resultNode,
          response.summary || "Your launch setup was saved successfully.",
          "success"
        );

        toast("Launch setup saved.", "success");
        announce("Launch setup saved.");
        doc.dispatchEvent(new CustomEvent("ff:onboarding:saved", { detail: response }));
        return response;
      } catch (error) {
        console.warn("[ff-app] onboarding submit failed", error);
        clearNodeMessage(statusNode);
        setNodeMessage(
          statusNode,
          error?.data?.message ||
            error.message ||
            "We could not save your launch setup right now. Please try again.",
          "warning"
        );
        toast("We could not save your launch setup right now.", "warning");
        return null;
      } finally {
        setButtonBusy(submitButton, false);
      }
    }

    finishButtons.forEach((button) => {
      button.addEventListener("click", submitOnboarding, true);
    });

    form.addEventListener("submit", submitOnboarding, true);
  }

  async function boot() {
    const app = {
      config,
      selectors,
      q,
      qa,
      openOverlay,
      closeOverlay,
      toast,
      announce,
      resolveApiBaseUrl,
      fetchJson,
      islands: {},
      state,
    };

    win.ffConfig = config;
    win.ffSelectors = selectors;
    win.FutureFundedApp = app;

    bindOverlay(selectors.openCheckout, selectors.closeCheckout, selectors.checkoutSheet);
    bindOverlay(selectors.openDrawer, selectors.closeDrawer, selectors.drawer);
    bindOverlay(selectors.openSponsor, selectors.closeSponsor, selectors.sponsorModal);
    bindOverlay(selectors.openTerms, selectors.closeTerms, selectors.termsModal);
    bindOverlay(selectors.openPrivacy, selectors.closePrivacy, selectors.privacyModal);
    bindOverlay(selectors.openOnboard, selectors.closeOnboard, selectors.onboardModal);

    bindEscapeClose();
    bindThemeToggle();
    bindBackToTop();
    bindFloatingDonate();
    bindVideoModal();
    bindSponsorModalExperience();

    await bootIslands(app);

    bindDonationRuntime(app);
    bindSponsorRuntime(app);
    bindOnboardingRuntime(app);

    root.dataset.ffBooted = "true";
    announce("FutureFunded page ready.");
  }

  if (doc.readyState === "loading") {
    doc.addEventListener(
      "DOMContentLoaded",
      () => {
        boot().catch((error) => {
          console.error("[ff-app] boot failed", error);
        });
      },
      { once: true }
    );
  } else {
    boot().catch((error) => {
      console.error("[ff-app] boot failed", error);
    });
  }
})();

/* FF_APP_NO_JS_BOOT_V1
   CSP-safe document boot. Replaces inline ff-no-js -> ff-js snippets.
*/
(() => {
  const root = document.documentElement;
  if (!root) return;

  root.classList.remove("ff-no-js");
  root.classList.add("ff-js");

  if (!root.dataset.ffJsReady) {
    root.dataset.ffJsReady = "true";
  }
})();


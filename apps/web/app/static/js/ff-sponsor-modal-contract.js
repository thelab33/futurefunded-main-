(() => {
  "use strict";

  const SELECTOR =
    "[data-ff-sponsor-modal], [data-ff-sponsor-sheet], #sponsor-modal, #sponsorModal";
  const TRIGGER_RE = /sponsor|package|community|featured|season|choose package/i;

  function visible(el) {
    if (!el || !(el instanceof Element)) return false;
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return (
      box.width > 60 &&
      box.height > 40 &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      Number(style.opacity || 1) > 0
    );
  }

  function mark(el, trigger) {
    if (!el) return false;
    el.setAttribute("data-ff-sponsor-modal", "");
    el.setAttribute("data-ff-sponsor-sheet", "");
    if (!el.id) el.id = "sponsor-modal";

    const tier = (
      trigger?.getAttribute("data-sponsor-tier") ||
      trigger?.getAttribute("data-ff-sponsor-tier") ||
      trigger?.getAttribute("data-tier") ||
      trigger?.textContent ||
      "sponsor"
    ).trim();

    el.setAttribute("data-ff-sponsor-tier", tier);
    return true;
  }

  function findDialog() {
    const explicit = Array.from(document.querySelectorAll(SELECTOR)).find(visible);
    if (explicit) return explicit;

    const candidates = Array.from(
      document.querySelectorAll(
        "[role='dialog'], [aria-modal='true'], dialog, [class*='modal'], [class*='sheet'], [data-ff-checkout-modal], [data-ff-checkout-sheet]"
      )
    ).filter(visible);

    return (
      candidates.find((el) =>
        /sponsor|package|business|recognition|logo/i.test(el.textContent || "")
      ) || candidates[0]
    );
  }

  function arm(trigger) {
    let tries = 0;
    const tick = () => {
      tries += 1;
      const dialog = findDialog();
      if (dialog && mark(dialog, trigger)) return;
      if (tries < 30) setTimeout(tick, 50);
    };
    tick();
  }

  document.addEventListener(
    "click",
    (event) => {
      const trigger = event.target?.closest?.("button,a,[role='button'],input");
      if (!trigger) return;

      const text = [
        trigger.textContent,
        trigger.getAttribute("aria-label"),
        trigger.getAttribute("data-sponsor-tier"),
        trigger.getAttribute("data-ff-sponsor-tier"),
        trigger.getAttribute("href"),
      ]
        .filter(Boolean)
        .join(" ");

      if (TRIGGER_RE.test(text)) arm(trigger);
    },
    true
  );

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(SELECTOR).forEach((el) => mark(el, null));
  });
})();

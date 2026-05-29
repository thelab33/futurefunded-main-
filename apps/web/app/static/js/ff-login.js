/*
  FutureFunded Login Runtime Authority
  File: apps/web/app/static/js/ff-login.js
  Version: login-runtime-authority-v1
*/

(() => {
  "use strict";

  const VERSION = "login-runtime-authority-v1";
  const root = document.querySelector("[data-ff-login-root]");
  if (!root || root.dataset.ffLoginRuntime === VERSION) return;

  root.dataset.ffLoginRuntime = VERSION;
  document.documentElement.classList.remove("ff-no-js");
  document.documentElement.dataset.ffLoginRuntime = VERSION;

  const form = root.querySelector("[data-ff-login-form]");
  const email = root.querySelector("[data-ff-login-email]");
  const password = root.querySelector("[data-ff-login-password]");
  const submit = root.querySelector("[data-ff-login-submit]");
  const toggle = root.querySelector("[data-ff-login-password-toggle]");

  root.querySelectorAll("[data-ff-login-reveal]").forEach((node, index) => {
    window.setTimeout(() => {
      node.setAttribute("data-ff-login-reveal", "true");
    }, 80 + index * 80);
  });

  if (toggle && password) {
    toggle.addEventListener("click", () => {
      const showing = password.type === "text";
      password.type = showing ? "password" : "text";
      toggle.textContent = showing ? "Show" : "Hide";
      toggle.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      password.focus({ preventScroll: true });
    });
  }

  if (form) {
    form.addEventListener("submit", (event) => {
      if (email && !email.checkValidity()) {
        event.preventDefault();
        email.focus();
        return;
      }

      if (password && !password.checkValidity()) {
        event.preventDefault();
        password.focus();
        return;
      }

      if (submit) {
        submit.setAttribute("aria-busy", "true");
        submit.disabled = true;
        submit.dataset.ffOriginalText = submit.textContent.trim();
        submit.textContent = "Signing in…";
      }

      window.dispatchEvent(
        new CustomEvent("ff:login:submit", {
          detail: {
            version: VERSION,
            email: email ? email.value.trim() : "",
          },
        }),
      );
    });
  }

  window.FutureFundedLogin = {
    version: VERSION,
    root,
    form,
    email,
    password,
  };

  console.info("[FutureFunded] Login runtime ready.", VERSION);
})();

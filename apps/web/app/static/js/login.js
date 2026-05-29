(() => {
  const root = document.querySelector("[data-ff-login-root]");
  if (!root) return;

  const password = root.querySelector("[data-ff-login-password]");
  const toggle = root.querySelector("[data-ff-login-password-toggle]");
  const form = root.querySelector("[data-ff-login-form]");
  const submit = root.querySelector("[data-ff-login-submit]");

  if (toggle && password) {
    toggle.addEventListener("click", () => {
      const showing = password.type === "text";
      password.type = showing ? "password" : "text";
      toggle.textContent = showing ? "Show" : "Hide";
      toggle.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  }

  if (form && submit) {
    form.addEventListener("submit", () => {
      submit.setAttribute("aria-busy", "true");
      submit.classList.add("is-loading");
    });
  }

  document.documentElement.classList.remove("ff-no-js");
  document.documentElement.classList.add("ff-js");
})();

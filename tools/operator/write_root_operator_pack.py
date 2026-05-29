import shutil
from datetime import datetime
from pathlib import Path

root = Path(".")
ts = datetime.now().strftime("%Y%m%d%H%M%S")

files = {
    "README.md": """# FutureFunded

FutureFunded is a premium fundraising platform for youth teams, nonprofits, schools, and clubs.

This repo is structured as a campaign-first product:
- `apps/web` is the canonical Flask/Jinja public app and platform shell
- `apps/api` is the FastAPI service edge for payments, sponsors, onboarding, analytics, and background tasks
- `packages/` is reserved for shared contracts, design tokens, and future reusable modules
- `tools/` is for audits, screenshots, smoke tests, and operator utilities

## Architecture

### Web
`apps/web`
- Flask app factory
- Jinja templates
- canonical public campaign funnel
- platform home, onboarding, and dashboard
- static CSS and JS islands served directly by Flask

### API
`apps/api`
- FastAPI service layer
- payment provider integrations
- sponsor lead workflows
- onboarding save/validate flows
- analytics and operational task hooks

## Current route map

### Web
- `/`
- `/platform`
- `/platform/onboarding`
- `/platform/dashboard`
- `/c/<slug>`
- `/sponsors`
- `/terms`
- `/privacy`

### API
- `/health`
- `/payments/config`
- `/payments/stripe/intent`
- `/payments/paypal/order`
- `/payments/paypal/capture`
- `/onboarding/save`
- `/onboarding/validate`
- `/analytics/event`
""",
    "Makefile": """SHELL := /bin/bash
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip
NPM ?= npm

export PYTHONPATH_WEB=apps/web
export PYTHONPATH_API=apps/api
export FLASK_APP_PATH=apps/web/wsgi.py

.DEFAULT_GOAL := help

help:
\t@echo "FutureFunded operator commands"

install:
\t$(PIP) install --upgrade pip setuptools wheel
\t$(PIP) install -e ".[dev]"
\t$(NPM) install

web:
\tPYTHONPATH=$(PYTHONPATH_WEB) FLASK_APP=$(FLASK_APP_PATH) $(PYTHON) -m flask run --host 127.0.0.1 --port 5000

api:
\tPYTHONPATH=$(PYTHONPATH_API) $(PYTHON) -m uvicorn asgi:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload

lint:
\t$(PYTHON) -m ruff check .
\t$(PYTHON) -m black --check .
\t$(NPM) run lint:js
\t$(NPM) run format:check

check-js:
\tnode --check apps/web/app/static/js/ff-app.js
\tnode --check apps/web/app/static/js/islands/donate.js
\tnode --check apps/web/app/static/js/islands/sponsor.js
\tnode --check apps/web/app/static/js/islands/onboarding.js
\tnode --check apps/web/app/static/js/islands/share.js
\tnode --check apps/web/app/static/js/islands/faq.js

test:
\t$(PYTHON) -m pytest -q || [ $$? -eq 5 ]
\t$(NPM) run test:js
""",
    ".editorconfig": """root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 2
trim_trailing_whitespace = true

[*.py]
indent_size = 4

[Makefile]
indent_style = tab
""",
    ".pre-commit-config.yaml": """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-merge-conflict
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
""",
    "package.json": """{
  "name": "futurefunded-tooling",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "lint:js": "eslint \\"apps/web/app/static/js/**/*.js\\" \\"tests/**/*.js\\"",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "test:js": "node --test tests/js/**/*.test.js",
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "@eslint/js": "^9.36.0",
    "@playwright/test": "^1.55.0",
    "eslint": "^9.36.0",
    "globals": "^16.4.0",
    "prettier": "^3.6.2"
  }
}
""",
    "eslint.config.mjs": """import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/**", "playwright-report/**", "test-results/**"] },
  js.configs.recommended,
  {
    files: ["apps/web/app/static/js/**/*.js", "tests/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: { ...globals.browser, ...globals.node }
    },
    rules: { "no-console": "off" }
  }
];
""",
    ".prettierrc.json": """{
  "printWidth": 100,
  "singleQuote": false,
  "trailingComma": "es5",
  "semi": true
}
""",
    "playwright.config.cjs": """const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5000",
    headless: true,
    trace: "retain-on-failure"
  }
});
""",
    "tests/js/contracts.test.js": """const test = require("node:test");
const assert = require("node:assert/strict");

test("operator pack placeholder", () => {
  assert.equal(true, true);
});
""",
    "tests/e2e/smoke.spec.js": """const { test, expect } = require("@playwright/test");

test("campaign page renders", async ({ page }) => {
  await page.goto("/c/connect-atx-elite");
  await expect(page.locator("body")).toContainText(/Support|Connect ATX Elite|Spring Fundraiser/i);
});
""",
}

for rel, content in files.items():
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(f"{path.name}.bak.{ts}")
        shutil.copy2(path, backup)
        print(f"[backup] {backup}")
    path.write_text(content, encoding="utf-8")
    print(f"[done] wrote {path}")

pyproject = Path("pyproject.toml")
text = pyproject.read_text(encoding="utf-8")

if "httpx>=0.28,<1" not in text:
    text = text.replace(
        '  "gunicorn>=25.3,<26",\n',
        '  "gunicorn>=25.3,<26",\n  "httpx>=0.28,<1",\n  "stripe>=13,<14",\n',
    )

if "dev = [\n" in text and "pre-commit>=4,<5" not in text:
    text = text.replace("dev = [\n", 'dev = [\n  "pre-commit>=4,<5",\n')

pyproject.write_text(text, encoding="utf-8")
print("[done] patched pyproject.toml")

gitignore = Path(".gitignore")
git_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
for extra in ["playwright-report/", "test-results/"]:
    if extra not in git_text:
        git_text = git_text.rstrip() + f"\\n{extra}\\n"
gitignore.write_text(git_text, encoding="utf-8")
print("[done] patched .gitignore")

package_lock = Path("package-lock.json")
if package_lock.exists() and not (root / "package.json").exists():
    package_lock.unlink()
    print("[done] removed stale package-lock.json")

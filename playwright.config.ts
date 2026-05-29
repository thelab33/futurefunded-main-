import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.FF_BASE_URL || "http://127.0.0.1:5000";

export default defineConfig({
  testDir: "tests/e2e",
  testMatch: ["**/*.spec.js", "**/*.spec.ts"],
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: process.env.PW_SKIP_WEBSERVER
    ? undefined
    : {
        command:
          "PYTHONPATH=apps/web FLASK_APP=apps/web/wsgi.py .venv/bin/python -m flask run --host 127.0.0.1 --port 5000",
        url: "http://127.0.0.1:5000/healthz",
        reuseExistingServer: !process.env.CI,
        timeout: 30_000,
      },
  projects: [
    {
      name: "chromium-desktop",
      use: {
        ...devices["Desktop Chrome"],
        browserName: "chromium",
      },
    },
    {
      name: "mobile-chrome",
      use: {
        ...devices["Pixel 5"],
        browserName: "chromium",
      },
    },
  ],
});

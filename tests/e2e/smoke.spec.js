const { test, expect } = require("@playwright/test");

test("healthz responds ok", async ({ request }) => {
  const response = await request.get("/healthz");
  expect(response.status()).toBe(200);

  const json = await response.json();
  expect(json.ok).toBe(true);
  expect(json.service).toBe("futurefunded-web");
});

test("platform page renders", async ({ page }) => {
  const response = await page.goto("/platform");
  expect(response).not.toBeNull();
  expect(response.status()).toBe(200);

  await expect(page.locator("body")).toContainText(/FutureFunded|fundraising|sponsor/i);
});

test("campaign page renders", async ({ page }) => {
  const response = await page.goto("/c/connect-atx-elite");
  expect(response).not.toBeNull();
  expect(response.status()).toBe(200);

  await expect(page.locator("body")).toContainText(/Support|Connect ATX Elite|Spring Fundraiser/i);
});

test("campaign slug canonicalizes to lowercase", async ({ page }) => {
  const response = await page.goto("/c/Connect-ATX-Elite");
  expect(response).not.toBeNull();
  expect(page.url()).toContain("/c/connect-atx-elite");
});

test("campaign checkout-state response is non-cacheable and non-indexable", async ({ request }) => {
  const response = await request.get("/c/connect-atx-elite?checkout=success&kind=sponsor");
  expect(response.status()).toBe(200);
  expect(response.headers()["cache-control"]).toBe("no-store, max-age=0");
  expect(response.headers()["x-robots-tag"]).toBe("noindex, nofollow");

  const text = await response.text();
  expect(text).toMatch(/Connect ATX Elite|Spring Fundraiser|Support/i);
});

test("sponsor honeypot endpoint returns hardened headers", async ({ request }) => {
  const response = await request.post("/sponsors/lead", {
    headers: {
      "content-type": "application/json",
      "x-request-id": "ff-e2e-sponsor-honeypot",
    },
    data: {
      website: "https://spam.example",
      business_name: "Bot Co",
      contact_email: "bot@example.com",
      campaign_slug: "connect-atx-elite",
    },
  });

  expect(response.status()).toBe(200);
  expect(response.headers()["cache-control"]).toBe("no-store, max-age=0");
  expect(response.headers()["x-robots-tag"]).toBe("noindex, nofollow");
  expect(response.headers()["x-request-id"]).toBe("ff-e2e-sponsor-honeypot");

  const json = await response.json();
  expect(json.ok).toBe(true);
  expect(json.message).toBe("Sponsor lead accepted.");
});

test("sponsors index returns sponsor resource json", async ({ request }) => {
  const response = await request.get("/sponsors");
  expect(response.status()).toBe(200);

  const json = await response.json();
  expect(json.ok).toBe(true);
  expect(json.resource).toBe("sponsors");
  expect(Array.isArray(json.tiers)).toBe(true);
  expect(Array.isArray(json.wall)).toBe(true);
});

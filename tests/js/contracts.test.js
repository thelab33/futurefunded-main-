const test = require("node:test");
const assert = require("node:assert/strict");

const API_BASE_URL = normalizeBaseUrl(
  process.env.FF_API_BASE_URL || process.env.FF_BASE_URL || "http://127.0.0.1:8000"
);

const WEB_BASE_URL = normalizeBaseUrl(process.env.FF_WEB_BASE_URL || API_BASE_URL);

function normalizeBaseUrl(value) {
  return String(value || "").replace(/\/+$/, "");
}

function jsonHeaders(requestId, extra = {}) {
  return {
    "content-type": "application/json",
    "x-request-id": requestId,
    ...extra,
  };
}

async function requestJson(path, options = {}) {
  const { baseUrl = API_BASE_URL, method = "GET", headers = {}, body, expectedStatus } = options;

  const url = `${baseUrl}${path}`;
  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await response.text();
  const json = parseJson(text);

  if (expectedStatus !== undefined) {
    assert.equal(
      response.status,
      expectedStatus,
      [
        `expected ${expectedStatus} from ${method} ${url}`,
        `got ${response.status}`,
        text ? `response: ${text}` : "response: <empty>",
      ].join("\n")
    );
  }

  return { response, json, text, url };
}

function parseJson(text) {
  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

test("payments config contract", async () => {
  const { response, json } = await requestJson("/payments/config", {
    headers: {
      "x-request-id": "ff-js-contract-payments-config",
    },
    expectedStatus: 200,
  });

  assert.equal(json?.ok, true);
  assert.equal(typeof json?.providers, "object");
  assert.ok(json?.providers?.stripe, "missing stripe provider");
  assert.ok(json?.providers?.paypal, "missing paypal provider");
  assert.equal(
    response.headers.get("cache-control"),
    "public, max-age=300, stale-while-revalidate=600"
  );
  assert.equal(response.headers.get("x-request-id"), "ff-js-contract-payments-config");
});

test("onboarding validate contract", async () => {
  const { response, json } = await requestJson("/onboarding/validate", {
    method: "POST",
    headers: jsonHeaders("ff-js-contract-onboarding-validate"),
    body: {
      organization_name: "Connect ATX Elite",
      campaign_name: "",
      operator_email: "",
      campaign_summary: "",
    },
    expectedStatus: 200,
  });

  assert.equal(json?.ok, false);
  assert.deepEqual(json?.missing_fields, ["campaign_name", "operator_email", "campaign_summary"]);
  assert.equal(json?.completion_ratio, 25);
  assert.equal(response.headers.get("cache-control"), "no-store, max-age=0");
  assert.equal(response.headers.get("x-request-id"), "ff-js-contract-onboarding-validate");
});

test("analytics event contract", async () => {
  const { response, json } = await requestJson("/analytics/event", {
    method: "POST",
    headers: jsonHeaders("ff-js-contract-analytics-event"),
    body: {
      event_type: "campaign_view",
      campaign_slug: "connect-atx-elite",
      metadata: {
        source: "contract-test",
        surface: "hero",
      },
    },
    expectedStatus: 200,
  });

  assert.equal(json?.event_type, "campaign_view");
  assert.match(json?.message || "", /accepted/i);
  assert.equal(response.headers.get("cache-control"), "no-store, max-age=0");
  assert.equal(response.headers.get("x-request-id"), "ff-js-contract-analytics-event");
  assert.equal(response.headers.get("x-analytics-event-type"), "campaign_view");
});

test("sponsors listing contract", async () => {
  const { json } = await requestJson("/sponsors", {
    baseUrl: WEB_BASE_URL,
    headers: {
      "x-request-id": "ff-js-contract-sponsors",
    },
    expectedStatus: 200,
  });

  assert.equal(json?.ok, true);
  assert.equal(json?.resource, "sponsors");
  assert.ok(Array.isArray(json?.tiers), "tiers should be an array");
  assert.ok(Array.isArray(json?.wall), "wall should be an array");
});

test("sponsor lead honeypot contract", async () => {
  const { response, json } = await requestJson("/sponsors/lead", {
    baseUrl: WEB_BASE_URL,
    method: "POST",
    headers: jsonHeaders("ff-js-contract-sponsor-lead"),
    body: {
      website: "https://spam.example",
      business_name: "Bot Co",
      contact_email: "bot@example.com",
      campaign_slug: "connect-atx-elite",
    },
    expectedStatus: 200,
  });

  assert.equal(json?.ok, true);
  assert.equal(json?.message, "Sponsor lead accepted.");
  assert.equal(response.headers.get("cache-control"), "no-store, max-age=0");
});

test("payments webhook rejects oversized valid json payload", async () => {
  const oversizedPayload = JSON.stringify({
    event: "oversized",
    data: "x".repeat(2_000_000),
  });

  const response = await fetch(`${API_BASE_URL}/payments/webhooks/stripe`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "stripe-signature": "test_signature",
    },
    body: oversizedPayload,
  });

  assert.equal(response.status, 413);
});

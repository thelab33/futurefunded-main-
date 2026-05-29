import { chromium } from "playwright";
import fs from "node:fs/promises";

const base = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const slug = process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";
const out = "artifacts/frontend-screenshots/post-action-trust-audit.json";
const proof = "docs/release-proof/post-action-trust-latest.json";

await fs.mkdir("artifacts/frontend-screenshots", { recursive: true });
await fs.mkdir("docs/release-proof", { recursive: true });

const browser = await chromium.launch({ headless: true });

async function inspect(url, kind, clickShare = false) {
  const page = await browser.newPage({ viewport: { width: 390, height: 1200 } });
  page.setDefaultTimeout(15_000);

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });

  await page.waitForSelector(
    `[data-ff-post-action-trust='true'][data-ff-post-action-kind='${kind}']`,
    { timeout: 15_000 }
  );

  await page.waitForTimeout(350);

  if (clickShare) {
    await page
      .locator(`[data-ff-post-action-trust='true'][data-ff-post-action-kind='${kind}'] [data-ff-post-action-primary]`)
      .first()
      .click({ timeout: 5000 });

    await page.waitForTimeout(650);
  }

  const data = await page.evaluate((expectedKind) => {
    const trust = document.querySelector(
      `[data-ff-post-action-trust='true'][data-ff-post-action-kind='${expectedKind}']`
    );
    const sponsorNote = document.querySelector("[data-ff-sponsor-review-note='true']");
    const drawer = document.querySelector("#qr-modal, [data-ff-share-drawer], [data-ff-qr-modal]");

    const drawerStyle = drawer ? getComputedStyle(drawer) : null;
    const drawerRect = drawer ? drawer.getBoundingClientRect() : null;

    return {
      runtime: window.FutureFundedPostActionTrust?.version || null,
      shareRuntime: window.FutureFundedShareQr?.version || null,
      trustExists: Boolean(trust),
      trustKind: trust?.getAttribute("data-ff-post-action-kind") || "",
      trustState: trust?.getAttribute("data-ff-post-action-state") || "",
      trustText: trust?.textContent?.replace(/\s+/g, " ").trim().slice(0, 800) || "",
      sponsorNoteExists: Boolean(sponsorNote),
      sponsorNoteText: sponsorNote?.textContent?.replace(/\s+/g, " ").trim().slice(0, 400) || "",
      shareDrawerVisible: Boolean(
        drawer &&
        !drawer.hidden &&
        drawer.getAttribute("aria-hidden") !== "true" &&
        drawerStyle.display !== "none" &&
        drawerStyle.visibility !== "hidden" &&
        Number(drawerStyle.opacity || "1") > 0 &&
        drawerRect.width > 20 &&
        drawerRect.height > 20
      ),
    };
  }, kind);

  await page.close();
  return data;
}

const paymentUrl = `${base}/c/${slug}?payment=success&session_id=cs_test_post_action_audit`;
const sponsorUrl = `${base}/c/${slug}?sponsor=submitted`;

const payment = await inspect(paymentUrl, "payment", true);
const sponsor = await inspect(sponsorUrl, "sponsor", false);

const checks = [
  {
    ok: payment.runtime === "post-action-trust-v2",
    label: "post-action runtime v2 exists",
    detail: payment.runtime || "missing",
  },
  {
    ok: payment.trustExists && payment.trustKind === "payment",
    label: "payment success trust panel renders",
    detail: payment.trustText,
  },
  {
    ok: /thank|checkout|payment|donation|support|stripe|ledger|momentum/i.test(payment.trustText),
    label: "payment panel has donor confidence copy",
  },
  {
    ok: payment.shareDrawerVisible,
    label: "payment success share CTA opens Share/QR drawer",
  },
  {
    ok: sponsor.trustExists && sponsor.trustKind === "sponsor",
    label: "sponsor handoff trust panel renders",
    detail: sponsor.trustText,
  },
  {
    ok: /review|public display|recognition|campaign owner|family-safe|dashboard/i.test(sponsor.trustText),
    label: "sponsor handoff explains review before public display",
  },
  {
    ok: sponsor.sponsorNoteExists,
    label: "sponsor section includes review note",
    detail: sponsor.sponsorNoteText,
  },
];

for (const check of checks) {
  console.log(`${check.ok ? "PASS" : "CHECK"} ${check.label}${check.detail ? ` — ${check.detail}` : ""}`);
}

const failed = checks.filter((check) => !check.ok);

const payload = {
  ok: failed.length === 0,
  checkedAt: new Date().toISOString(),
  paymentUrl,
  sponsorUrl,
  payment,
  sponsor,
  checks,
};

await fs.writeFile(out, `${JSON.stringify(payload, null, 2)}\n`);
await fs.writeFile(proof, `${JSON.stringify(payload, null, 2)}\n`);

console.log(`\nWrote ${out}`);
console.log(`Wrote ${proof}`);
console.log(`Summary: ${checks.length - failed.length}/${checks.length} passed`);

await browser.close();

if (failed.length) process.exit(1);

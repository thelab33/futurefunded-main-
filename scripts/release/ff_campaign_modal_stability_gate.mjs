import fs from "node:fs"
import path from "node:path"
import { chromium } from "playwright"

const baseUrl = process.env.FF_BASE_URL || "http://127.0.0.1:5000"
const outDir = process.env.OUT_DIR || "audit_outputs/campaign-modal-stability-v3/latest"
const campaignUrl = `${baseUrl}/c/connect-atx-elite?modal_probe=${Date.now()}`

fs.mkdirSync(outDir, { recursive: true })

const viewports = [
  { name: "mobile", width: 390, height: 844, isMobile: true },
  { name: "tablet", width: 768, height: 1024, isMobile: false },
  { name: "desktop", width: 1440, height: 1000, isMobile: false }
]

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function snapshot(page) {
  return await page.evaluate(() => {
    const checkout = document.querySelector("[data-ff-checkout-modal], [data-ff-embedded-checkout-shell]")
    const sponsor = document.querySelector("[data-ff-sponsor-modal]")

    const visible = (el) => {
      if (!el) return false
      const rect = el.getBoundingClientRect()
      const style = getComputedStyle(el)
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden"
    }

    return {
      bodyOverflow: getComputedStyle(document.body).overflow,
      htmlOverflow: getComputedStyle(document.documentElement).overflow,
      modalOpenClass:
        document.documentElement.classList.contains("ff-modal-open") ||
        document.body.classList.contains("ff-modal-open"),
      checkoutHidden: checkout ? checkout.hasAttribute("hidden") : null,
      checkoutVisible: visible(checkout),
      checkoutState: checkout ? (
        checkout.getAttribute("data-ff-state") ||
        checkout.getAttribute("data-ff-checkout-state") ||
        checkout.getAttribute("data-ff-modal-state")
      ) : null,
      sponsorHidden: sponsor ? sponsor.hasAttribute("hidden") : null,
      sponsorVisible: visible(sponsor),
      openCheckoutTriggers: document.querySelectorAll("[data-ff-open-checkout]").length,
      backgroundDonationAmounts: document.querySelectorAll(".ff-donationAmount[data-ff-checkout-amount]").length,
      modalCheckoutAmounts: document.querySelectorAll("[data-ff-checkout-modal] .ff-checkoutAmount, [data-ff-embedded-checkout-shell] .ff-checkoutAmount").length,
      closeButtons: document.querySelectorAll("[data-ff-close-embedded-checkout]").length
    }
  })
}

async function installLagProbe(page) {
  await page.addInitScript(() => {
    window.__ffLag = { maxLag: 0, ticks: 0, errors: [], longTasks: [] }
    let last = performance.now()

    setInterval(() => {
      const now = performance.now()
      const lag = Math.max(0, now - last - 250)
      window.__ffLag.maxLag = Math.max(window.__ffLag.maxLag, lag)
      window.__ffLag.ticks += 1
      last = now
    }, 250)

    window.addEventListener("error", (event) => {
      window.__ffLag.errors.push(String(event.message || "window error"))
    })

    window.addEventListener("unhandledrejection", (event) => {
      window.__ffLag.errors.push(String(event.reason || "unhandled rejection"))
    })

    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          window.__ffLag.longTasks.push({
            startTime: Math.round(entry.startTime),
            duration: Math.round(entry.duration),
            name: entry.name
          })
        }
      })
      observer.observe({ type: "longtask", buffered: true })
    } catch {}
  })
}

async function safe(row, label, fn) {
  const started = Date.now()

  try {
    await Promise.race([
      fn(),
      new Promise((_, reject) => setTimeout(() => reject(new Error(`timeout in ${label}`)), 15000))
    ])

    row.steps.push({ label, ok: true, ms: Date.now() - started })
  } catch (error) {
    row.steps.push({ label, ok: false, ms: Date.now() - started, error: String(error.message || error) })
    row.failures.push(`${label}: ${String(error.message || error)}`)
  }
}

async function closeCheckout(page) {
  const visibleClose = page.locator(
    "[data-ff-checkout-modal] .ff-embeddedCheckout__head [data-ff-close-embedded-checkout], " +
    "[data-ff-embedded-checkout-shell] .ff-embeddedCheckout__head [data-ff-close-embedded-checkout], " +
    "[data-ff-checkout-modal] [aria-label='Close checkout']:not(.ff-embeddedCheckout__backdrop)"
  ).first()

  if (await visibleClose.count()) {
    await visibleClose.click({ timeout: 8000 })
  } else {
    await page.keyboard.press("Escape")
  }

  await sleep(700)
}

async function runViewport(browser, viewport) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    isMobile: viewport.isMobile,
    reducedMotion: "reduce"
  })

  const page = await context.newPage()
  await installLagProbe(page)

  const row = {
    viewport: viewport.name,
    status: null,
    failures: [],
    pageErrors: [],
    consoleErrors: [],
    requestFailures: [],
    steps: [],
    before: null,
    after: null,
    lag: null
  }

  page.on("pageerror", (error) => row.pageErrors.push(String(error.message || error)))
  page.on("console", (msg) => {
    if (msg.type() === "error") row.consoleErrors.push(msg.text())
  })
  page.on("requestfailed", (request) => {
    row.requestFailures.push({ url: request.url(), error: request.failure()?.errorText || "failed" })
  })

  await safe(row, "load campaign", async () => {
    const response = await page.goto(campaignUrl, { waitUntil: "networkidle", timeout: 45000 })
    row.status = response?.status() || null
  })

  await safe(row, "snapshot before", async () => {
    row.before = await snapshot(page)
  })

  await safe(row, "scroll stress", async () => {
    const height = await page.evaluate(() => document.documentElement.scrollHeight)
    for (const y of [0, height * 0.25, height * 0.5, height * 0.85, 0]) {
      await page.evaluate((top) => window.scrollTo({ top, behavior: "auto" }), Math.round(y))
      await sleep(220)
    }
  })

  await safe(row, "open checkout", async () => {
    const trigger = page.locator("[data-ff-open-checkout]").first()
    await trigger.waitFor({ state: "visible", timeout: 10000 })
    await trigger.click({ timeout: 10000 })
    await page.locator("[data-ff-checkout-modal], [data-ff-embedded-checkout-shell]").first().waitFor({ state: "visible", timeout: 10000 })
    await sleep(700)
  })

  await safe(row, "modal checkout amount sweep", async () => {
    const buttons = page.locator(
      "[data-ff-checkout-modal] .ff-checkoutAmount[data-ff-checkout-amount], " +
      "[data-ff-embedded-checkout-shell] .ff-checkoutAmount[data-ff-checkout-amount], " +
      "[data-ff-checkout-modal] [data-ff-amount-button='checkout'], " +
      "[data-ff-embedded-checkout-shell] [data-ff-amount-button='checkout']"
    )

    const count = Math.min(await buttons.count(), 5)
    if (!count) throw new Error("no modal checkout amount buttons found")

    for (let i = 0; i < count; i += 1) {
      const button = buttons.nth(i)
      await button.scrollIntoViewIfNeeded({ timeout: 6000 })
      await button.click({ timeout: 8000 })
      await sleep(140)
    }
  })

  await safe(row, "close checkout with panel close", async () => {
    await closeCheckout(page)
  })

  await safe(row, "verify checkout closed", async () => {
    const snap = await snapshot(page)
    if (snap.checkoutVisible || snap.checkoutState === "open") {
      throw new Error(`checkout still open: ${JSON.stringify(snap)}`)
    }
  })

  await safe(row, "open sponsor modal after checkout close", async () => {
    const trigger = page.locator("[data-ff-open-sponsor], [data-ff-sponsor-trigger]").first()
    if (!(await trigger.count())) return

    await trigger.scrollIntoViewIfNeeded({ timeout: 8000 })
    await trigger.click({ timeout: 8000 })
    await sleep(700)
  })

  await safe(row, "close sponsor modal", async () => {
    const close = page.locator(
      "[data-ff-sponsor-modal] .ff-sponsorModal__close, " +
      "[data-ff-sponsor-modal] [data-ff-sponsor-close]:not(.ff-sponsorModal__backdrop)"
    ).first()

    if (await close.count()) {
      await close.click({ timeout: 8000 })
    } else {
      await page.keyboard.press("Escape")
    }

    await sleep(700)
  })

  await safe(row, "rapid checkout open-close cycle", async () => {
    const trigger = page.locator("[data-ff-open-checkout]").first()

    for (let i = 0; i < 3; i += 1) {
      await trigger.scrollIntoViewIfNeeded({ timeout: 8000 })
      await trigger.click({ timeout: 8000 })
      await sleep(250)
      await closeCheckout(page)
    }
  })

  await safe(row, "snapshot after", async () => {
    row.after = await snapshot(page)
    row.lag = await page.evaluate(() => window.__ffLag || null)
  })

  await page.screenshot({
    path: path.join(outDir, `campaign-${viewport.name}-modal-stability.png`),
    fullPage: true,
    animations: "disabled"
  })

  if (row.status !== 200) row.failures.push(`bad status ${row.status}`)
  if (row.pageErrors.length) row.failures.push(`page errors ${row.pageErrors.length}`)
  if (row.requestFailures.length) row.failures.push(`request failures ${row.requestFailures.length}`)
  if (row.lag?.maxLag > 1200) row.failures.push(`event loop lag ${Math.round(row.lag.maxLag)}ms`)
  if ((row.lag?.longTasks || []).some((task) => task.duration > 900)) row.failures.push("long task over 900ms")

  const modalActuallyOpen = row.after?.checkoutVisible || row.after?.sponsorVisible
  if (!modalActuallyOpen && row.after?.modalOpenClass) row.failures.push("modal-open class stuck after close")
  if (!modalActuallyOpen && row.after?.bodyOverflow === "hidden") row.failures.push("body overflow hidden stuck after close")

  await context.close()
  return row
}

const browser = await chromium.launch({ headless: true })
const results = []

for (const viewport of viewports) {
  console.log(`Probing ${viewport.name}`)
  results.push(await runViewport(browser, viewport))
}

await browser.close()

const failures = results.flatMap((row) => row.failures.map((failure) => `${row.viewport}: ${failure}`))

const summary = { generatedAt: new Date().toISOString(), campaignUrl, failures, results }

fs.writeFileSync(path.join(outDir, "campaign-modal-stability.json"), JSON.stringify(summary, null, 2))

const report = [
  "# Campaign Modal Stability Probe V3",
  "",
  `URL: ${campaignUrl}`,
  `Failures: ${failures.length}`,
  "",
  ...results.map((row) => [
    `## ${row.viewport}`,
    "",
    `- Status: ${row.status}`,
    `- Failures: ${row.failures.length ? row.failures.join("; ") : "none"}`,
    `- Page errors: ${row.pageErrors.length}`,
    `- Console errors: ${row.consoleErrors.length}`,
    `- Request failures: ${row.requestFailures.length}`,
    `- Max lag: ${row.lag ? Math.round(row.lag.maxLag) : "n/a"}ms`,
    `- Long tasks: ${row.lag?.longTasks?.length || 0}`,
    `- Body overflow after: ${row.after?.bodyOverflow}`,
    `- Modal-open after: ${row.after?.modalOpenClass}`,
    `- Checkout visible after: ${row.after?.checkoutVisible}`,
    `- Sponsor visible after: ${row.after?.sponsorVisible}`,
    `- Background donation amount controls: ${row.before?.backgroundDonationAmounts}`,
    `- Modal checkout amount controls: ${row.before?.modalCheckoutAmounts}`,
    `- Screenshot: campaign-${row.viewport}-modal-stability.png`,
    ""
  ].join("\n"))
].join("\n")

fs.writeFileSync(path.join(outDir, "report.md"), report)

console.log(`MODAL_STABILITY_OUT=${outDir}`)
console.log(`MODAL_STABILITY_REPORT=${path.join(outDir, "report.md")}`)

if (failures.length) {
  console.log(`CAMPAIGN_MODAL_STABILITY=FAIL failures=${failures.length}`)
  process.exit(1)
}

console.log("CAMPAIGN_MODAL_STABILITY=PASS")

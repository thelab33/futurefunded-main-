const { chromium } = require("playwright")

const BASE = process.env.FF_BASE_URL || "http://127.0.0.1:5000"
const ROUTE = "/c/connect-atx-elite"

const scenarios = [
  { name: "js-off", javaScriptEnabled: false, blockExternal: true, blockCampaignJs: false },
  { name: "js-on-block-external", javaScriptEnabled: true, blockExternal: true, blockCampaignJs: false },
  { name: "js-on-block-campaign-js", javaScriptEnabled: true, blockExternal: true, blockCampaignJs: true },
  { name: "js-on-normal", javaScriptEnabled: true, blockExternal: false, blockCampaignJs: false }
]

function timeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} timeout after ${ms}ms`)), ms))
  ])
}

async function run() {
  const browser = await chromium.launch({ headless: true })

  for (const scenario of scenarios) {
    console.log("")
    console.log("================================")
    console.log(`Scenario: ${scenario.name}`)
    console.log("================================")

    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      javaScriptEnabled: scenario.javaScriptEnabled
    })

    const page = await context.newPage()
    page.setDefaultTimeout(8000)
    page.setDefaultNavigationTimeout(12000)

    const consoleMessages = []
    const pageErrors = []
    const failedRequests = []

    page.on("console", msg => {
      if (["error", "warning"].includes(msg.type())) {
        consoleMessages.push(`${msg.type()}: ${msg.text()}`.slice(0, 260))
      }
    })

    page.on("pageerror", err => {
      pageErrors.push(String(err.message || err).slice(0, 260))
    })

    page.on("requestfailed", req => {
      failedRequests.push(`${req.url()} :: ${req.failure()?.errorText || "failed"}`.slice(0, 260))
    })

    if (scenario.blockExternal || scenario.blockCampaignJs) {
      await page.route("**/*", route => {
        const url = route.request().url()

        if (scenario.blockCampaignJs && url.includes("/static/js/ff-campaign.js")) {
          return route.abort()
        }

        if (scenario.blockExternal) {
          const isLocal =
            url.startsWith(BASE) ||
            url.startsWith("http://127.0.0.1:5000") ||
            url.startsWith("http://localhost:5000")

          const isHeavy = /\.(png|jpe?g|gif|webp|svg|mp4|webm|mov|woff2?|ttf|otf)(\?|$)/i.test(url)

          if (!isLocal || isHeavy) {
            return route.abort()
          }
        }

        return route.continue()
      })
    }

    const url = new URL(ROUTE, BASE)
    url.searchParams.set("css_v", `campaign-isolate-${Date.now()}`)

    try {
      console.log("→ goto start")
      const response = await timeout(
        page.goto(url.toString(), { waitUntil: "domcontentloaded", timeout: 12000 }),
        14000,
        "goto"
      )
      console.log(`→ goto done: HTTP ${response ? response.status() : "NO_RESPONSE"}`)

      console.log("→ settle start")
      await timeout(page.waitForTimeout(1000), 2000, "settle")
      console.log("→ settle done")

      console.log("→ evaluate start")
      const report = await timeout(
        page.evaluate(async () => {
          const html = document.documentElement
          const body = document.body
          const scrollEl = document.scrollingElement || document.documentElement
          const beforeY = window.scrollY

          window.scrollTo(0, Math.max(0, scrollEl.scrollHeight - scrollEl.clientHeight))
          await new Promise(resolve => setTimeout(resolve, 250))

          const fixedBlockers = [...document.body.querySelectorAll("*")]
            .map(el => {
              const cs = getComputedStyle(el)
              const r = el.getBoundingClientRect()
              const z = Number.parseInt(cs.zIndex, 10)
              return {
                tag: el.tagName.toLowerCase(),
                id: el.id || "",
                cls: String(el.className || "").slice(0, 120),
                position: cs.position,
                display: cs.display,
                visibility: cs.visibility,
                opacity: cs.opacity,
                pointerEvents: cs.pointerEvents,
                zIndex: cs.zIndex,
                rect: {
                  w: Math.round(r.width),
                  h: Math.round(r.height),
                  y: Math.round(r.y)
                },
                blocks:
                  ["fixed", "sticky"].includes(cs.position) &&
                  cs.display !== "none" &&
                  cs.visibility !== "hidden" &&
                  cs.pointerEvents !== "none" &&
                  r.width > window.innerWidth * 0.75 &&
                  r.height > window.innerHeight * 0.35 &&
                  (Number.isNaN(z) || z >= 20)
              }
            })
            .filter(x => x.blocks)
            .slice(0, 8)

          return {
            title: document.title,
            h1: [...document.querySelectorAll("h1")].map(h => h.textContent.trim().replace(/\s+/g, " ")).slice(0, 4),
            htmlClass: html.className,
            bodyClass: body.className,
            htmlPage: html.getAttribute("data-ff-page"),
            bodySurface: body.getAttribute("data-ff-surface"),
            textLength: body.innerText.trim().length,
            scrollHeight: scrollEl.scrollHeight,
            clientHeight: scrollEl.clientHeight,
            scrollMoved: window.scrollY > beforeY + 20,
            fixedBlockers,
            scripts: [...document.querySelectorAll("script[src]")].map(s => s.getAttribute("src")),
            css: [...document.querySelectorAll('link[rel="stylesheet"]')].map(s => s.getAttribute("href")),
            iframes: [...document.querySelectorAll("iframe")].map(f => f.src).slice(0, 8)
          }
        }),
        10000,
        "evaluate"
      )

      console.log("→ evaluate done")
      console.log(JSON.stringify(report, null, 2))

      if (consoleMessages.length) {
        console.log("console warnings/errors:")
        console.log(consoleMessages.slice(0, 10).map(x => `  - ${x}`).join("\n"))
      }

      if (pageErrors.length) {
        console.log("page errors:")
        console.log(pageErrors.slice(0, 10).map(x => `  - ${x}`).join("\n"))
      }

      if (failedRequests.length) {
        console.log("failed requests:")
        console.log(failedRequests.slice(0, 10).map(x => `  - ${x}`).join("\n"))
      }
    } catch (err) {
      console.log(`❌ scenario failed: ${err.message}`)

      if (consoleMessages.length) {
        console.log("console warnings/errors:")
        console.log(consoleMessages.slice(0, 10).map(x => `  - ${x}`).join("\n"))
      }

      if (pageErrors.length) {
        console.log("page errors:")
        console.log(pageErrors.slice(0, 10).map(x => `  - ${x}`).join("\n"))
      }

      if (failedRequests.length) {
        console.log("failed requests:")
        console.log(failedRequests.slice(0, 10).map(x => `  - ${x}`).join("\n"))
      }
    }

    await context.close().catch(() => {})
  }

  await browser.close().catch(() => {})
}

run().catch(err => {
  console.error(err)
  process.exit(1)
})

const { chromium } = require("playwright")

const base = "http://127.0.0.1:5000"
const cssv = process.env.FF_ASSET_V || `hero-bg-audit-${Date.now()}`

const pages = [
  ["platform", "/platform/", [".ff-platformHero__copy"]],
  ["campaign", "/c/connect-atx-elite", [".ff-campaignHero__story", ".ff-donatePanel"]],
  ["login", "/platform/login", [".ff-loginAuthority__hero", ".ff-loginAuthority__card"]],
  ["onboarding", "/platform/onboarding", [".ff-onboardHero", ".ff-onboardReadiness"]],
  ["dashboard-locked", "/platform/dashboard", [".ff-dashboardLockedHero", ".ff-dashboardLockedPanel"]],
]

function pageUrl(route) {
  return `${base}${route}${route.includes("?") ? "&" : "?"}css_v=${cssv}`
}

async function main() {
  const browser = await chromium.launch({ headless: true })

  for (const [name, route, selectors] of pages) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
    const url = pageUrl(route)

    let res
    try {
      res = await page.goto(url, { waitUntil: "networkidle", timeout: 30000 })
    } catch (error) {
      console.log(`\n=== ${name.toUpperCase()} LOAD ERROR ===`)
      console.log(error.message)
      await page.close()
      continue
    }

    const data = await page.evaluate((selectors) => {
      const root = getComputedStyle(document.documentElement)

      const vars = {
        strong: root.getPropertyValue("--ff-hero-surface-warm-strong").trim(),
        panel: root.getPropertyValue("--ff-hero-surface-warm-panel").trim(),
        accent: root.getPropertyValue("--ff-accent-warm").trim(),
      }

      return selectors.map((selector) => {
        const el = document.querySelector(selector)

        if (!el) {
          return {
            selector,
            count: document.querySelectorAll(selector).length,
            found: false,
          }
        }

        const cs = getComputedStyle(el)
        const rect = el.getBoundingClientRect()
        const bg = `${cs.backgroundImage} ${cs.backgroundColor}`

        return {
          selector,
          count: document.querySelectorAll(selector).length,
          found: true,
          rect: {
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            w: Math.round(rect.width),
            h: Math.round(rect.height),
          },
          vars,
          backgroundImage: cs.backgroundImage.slice(0, 700),
          backgroundColor: cs.backgroundColor,
          hasWarmPeach:
            bg.includes("255, 196, 137") ||
            bg.includes("255,196,137") ||
            bg.includes("255, 205, 155") ||
            bg.includes("255,205,155") ||
            bg.includes("255, 232, 196") ||
            bg.includes("255,232,196"),
        }
      })
    }, selectors)

    console.log(`\n=== ${name.toUpperCase()} status=${res ? res.status() : "none"} ===`)
    console.log(`url: ${url}`)

    for (const item of data) {
      console.log(`${item.selector}`)
      console.log(`  count: ${item.count}`)
      console.log(`  found: ${item.found}`)

      if (item.found) {
        console.log(`  rect: ${JSON.stringify(item.rect)}`)
        console.log(`  vars.strong: ${Boolean(item.vars.strong)}`)
        console.log(`  vars.panel: ${Boolean(item.vars.panel)}`)
        console.log(`  accent: ${item.vars.accent || "MISSING"}`)
        console.log(`  hasWarmPeach: ${item.hasWarmPeach}`)
        console.log(`  bgColor: ${item.backgroundColor}`)
        console.log(`  bgImage: ${item.backgroundImage}`)
      }
    }

    await page.close()
  }

  await browser.close()
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})

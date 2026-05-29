import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

URL = "http://127.0.0.1:5000/c/connect-atx-elite"
OUT = Path("artifacts/screenshots/live-header-audit.png")
OUT.parent.mkdir(parents=True, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1100}, device_scale_factor=1
        )

        await page.goto(URL, wait_until="networkidle")

        data = await page.evaluate(
            """
        () => {
          const chrome = document.querySelector('.ff-chrome.ff-campaignHeaderV3');
          const bar = document.querySelector('.ff-campaignHeaderV3__bar');
          const inner = document.querySelector('.ff-campaignHeaderV3__inner');
          const main = document.querySelector('.ff-main--campaignV1');
          const links = [...document.querySelectorAll('link[rel="stylesheet"]')].map(l => l.href);

          function info(el) {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            return {
              className: el.className,
              x: Math.round(r.x),
              y: Math.round(r.y),
              width: Math.round(r.width),
              height: Math.round(r.height),
              position: cs.position,
              display: cs.display,
              paddingTop: cs.paddingTop,
              paddingBottom: cs.paddingBottom,
              marginTop: cs.marginTop,
              zIndex: cs.zIndex,
              background: cs.backgroundColor,
              overflow: cs.overflow,
            };
          }

          return {
            url: location.href,
            stylesheets: links,
            chrome: info(chrome),
            bar: info(bar),
            inner: info(inner),
            main: info(main),
            headerText: chrome ? chrome.innerText.replace(/\\s+/g, ' ').trim() : null,
          };
        }
        """
        )

        print("\\n=== LIVE CAMPAIGN HEADER AUDIT ===\\n")
        print("URL:", data["url"])
        print("\\nStylesheets:")
        for href in data["stylesheets"]:
            print(" -", href)

        print("\\nChrome:", data["chrome"])
        print("Bar:", data["bar"])
        print("Inner:", data["inner"])
        print("Main:", data["main"])
        print("\\nHeader text:", data["headerText"])

        await page.screenshot(path=str(OUT), full_page=True)
        print(f"\\n✅ Fresh screenshot saved: {OUT}")

        await browser.close()


asyncio.run(main())

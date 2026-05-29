import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

URL = "http://127.0.0.1:5000/c/connect-atx-elite"
OUT = Path("artifacts/screenshots/live-story-audit.png")
OUT.parent.mkdir(parents=True, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1100},
            device_scale_factor=1,
        )

        await page.goto(URL, wait_until="networkidle")

        data = await page.evaluate(
            """
        () => {
          const story = document.querySelector('#story');
          const impact = document.querySelector('#impact');
          const mini = document.querySelector('.ff-impactLedgerMiniV1');
          const marker = document.documentElement.innerHTML.includes('ff:campaign-story-impact-ledger:v2');

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
              display: cs.display,
              visibility: cs.visibility,
              opacity: cs.opacity,
              position: cs.position,
              overflow: cs.overflow,
            };
          }

          return {
            marker,
            story: info(story),
            impact: info(impact),
            mini: info(mini),
            storyText: story ? story.innerText.replace(/\\s+/g, ' ').trim().slice(0, 500) : null,
          };
        }
        """
        )

        print("\\n=== LIVE CAMPAIGN STORY AUDIT ===\\n")
        print("Marker rendered:", data["marker"])
        print("Story:", data["story"])
        print("Impact anchor:", data["impact"])
        print("Mini:", data["mini"])
        print("\\nStory text:", data["storyText"])

        story = await page.query_selector("#story")
        if story:
            await story.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

        await page.screenshot(path=str(OUT), full_page=False)
        print(f"\\n✅ Story screenshot saved: {OUT}")

        await browser.close()


asyncio.run(main())

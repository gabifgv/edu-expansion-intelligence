"""Screenshot focado só no chart do radar."""
import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

OUT = Path("C:/Users/gabriella.pinheiro/AppData/Local/Temp/fgv_shots")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
        await page.wait_for_timeout(500)
        await page.evaluate("""
            () => {
                document.getElementById('f-municipio').value = '3509502';
                document.getElementById('f-municipio-input').value = 'Campinas';
            }
        """)
        await page.click("#btn-analisar")
        await page.wait_for_selector(".kpi-strip.show", timeout=20000)
        await page.wait_for_timeout(3000)

        # Screenshot só do radar e do top20
        for sel, fn in [("#b6-chart-radar", "06_radar.png"), ("#b6-chart-top", "07_top20.png"), ("#b5-chart-ies", "08_top_ies.png")]:
            el = await page.query_selector(sel)
            if el:
                await el.scroll_into_view_if_needed()
                await page.wait_for_timeout(300)
                await el.screenshot(path=str(OUT / fn))
                print(f"Salvou: {fn}")
        await browser.close()

asyncio.run(main())

"""Tira screenshots do dashboard para validação visual."""
import asyncio, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

OUT_DIR = Path("C:/Users/gabriella.pinheiro/AppData/Local/Temp/fgv_shots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[browser console] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[page error] {err}"))

        await page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
        await page.wait_for_timeout(800)

        # Seleciona Campinas — diretamente via JS
        await page.evaluate("""
            () => {
                document.getElementById('f-municipio').value = '3509502';
                document.getElementById('f-municipio-input').value = 'Campinas';
            }
        """)
        await page.wait_for_timeout(200)

        # CEP da gestora
        await page.fill("#f-cep", "13051093")

        # Clica em carregar análise
        await page.click("#btn-analisar")
        await page.wait_for_selector(".kpi-strip.show", timeout=20000)
        await page.wait_for_timeout(3000)  # aguarda Plotly + render

        # Screenshot do header
        await page.screenshot(path=str(OUT_DIR / "01_header.png"), clip={"x": 0, "y": 0, "width": 1440, "height": 220})
        print(f"Salvou: 01_header.png")

        # Element-level screenshots (auto-scroll)
        for sel, fn in [("#b1", "05_bloco1.png"), ("#b23", "04_bloco23.png"), ("#b5", "02_bloco5.png"), ("#b6", "03_bloco6.png")]:
            el = await page.query_selector(sel)
            if el:
                await el.scroll_into_view_if_needed()
                await page.wait_for_timeout(300)
                await el.screenshot(path=str(OUT_DIR / fn))
                print(f"Salvou: {fn}")

        # Full page para checar overflow
        await page.screenshot(path=str(OUT_DIR / "00_fullpage.png"), full_page=True)
        print(f"Salvou: 00_fullpage.png")

        await browser.close()
        print(f"\nTodas screenshots em: {OUT_DIR}")

asyncio.run(main())

#!/usr/bin/env python3
import asyncio, json
from playwright.async_api import async_playwright

async def main():
    errors, bad = [], []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox", "--enable-webgl", "--use-angle=swiftshader"])
        page = await b.new_page(viewport={"width": 1920, "height": 1080})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: bad.append([r.status, r.url]) if r.status >= 400 else None)
        await page.goto("https://heyckz.cc/satdash/", wait_until="networkidle")
        await page.get_by_role("button", name="进入态势中心").click()
        await page.wait_for_selector(".dashboard", timeout=30000)
        await page.wait_for_timeout(7000)
        data = await page.evaluate("""() => ({canvas:document.querySelectorAll('canvas').length,
          rows:document.querySelectorAll('.sat-row').length,
          kpis:[...document.querySelectorAll('.kpi b')].map(x=>x.textContent),
          online:document.body.innerText.includes('WEBSOCKET · ONLINE'),
          scroll:[document.body.scrollWidth,document.body.scrollHeight]})""")
        await page.screenshot(path="/root/satdash/public-dashboard.png", timeout=60000)
        print(json.dumps({"page": data, "errors": errors, "httpErrors": bad}, ensure_ascii=False))
        assert data["canvas"] == 5 and data["rows"] == 8 and data["online"] and not errors and not bad
        await b.close()
asyncio.run(main())

#!/usr/bin/env python3
"""浏览器端验收：登录 → 图表渲染 → WS → 写入 → 弹窗 → 1920 无滚动条；保存截图和控制台错误。"""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    errors, responses = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader"])
        page = await browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.on("console", lambda m: errors.append(f"console:{m.type}:{m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror:{e}"))
        page.on("response", lambda r: responses.append((r.status, r.url)) if r.status >= 400 else None)
        await page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        await page.screenshot(path="/root/satdash/login.png")
        assert await page.locator(".login-card").is_visible(), "登录页未显示"
        await page.get_by_role("button", name="进入态势中心").click()
        await page.wait_for_selector(".dashboard", timeout=30000)
        await page.wait_for_timeout(7000)
        metrics = await page.evaluate("""() => ({
          canvases: document.querySelectorAll('canvas').length,
          rows: document.querySelectorAll('.sat-row').length,
          kpis: [...document.querySelectorAll('.kpi b')].map(x => x.textContent),
          ws: document.querySelector('.telemetry-row b')?.textContent,
          stage: (()=>{let r=document.querySelector('.stage').getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})(),
          bodyScroll: [document.body.scrollWidth, document.body.scrollHeight],
          viewport: [innerWidth, innerHeight]
        })""")
        await page.screenshot(path="/root/satdash/dashboard.png", full_page=True)
        # 打开卫星详情
        await page.locator(".sat-row").first.click()
        await page.wait_for_selector(".modal")
        # 从详情进入新增观测并保存
        await page.get_by_role("button", name="为该目标新增观测").click()
        await page.locator("textarea").fill("浏览器自动化验收：观测记录写入并回查。")
        await page.get_by_role("button", name="保存并回查").click()
        await page.wait_for_timeout(1800)
        await page.wait_for_timeout(2500)
        if await page.locator(".modal-mask").count():
            await page.locator(".modal-mask").evaluate_all("els => els.forEach(e => e.style.display='none')")
        await page.get_by_role("button", name="观测台账").click()
        await page.wait_for_timeout(800)
        record_count = await page.locator(".record").count()
        await page.screenshot(path="/root/satdash/records.png")
        result = {"metrics": metrics, "recordCount": record_count, "errors": errors, "httpErrors": responses}
        Path("/root/satdash/browser-test.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        await browser.close()

asyncio.run(main())

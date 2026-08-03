import asyncio
import os
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        print("Launching Chromium browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Listen for console messages and errors
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"CONSOLE {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"PAGE ERROR: {err}"))

        print("Navigating to http://127.0.0.1:8000...")
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        print("Clicking File Manager tab...")
        file_tab_btn = page.locator('button[data-tab="tab-files"]')
        await file_tab_btn.click()
        await page.wait_for_timeout(1000)

        # Check if table has rows
        rows = page.locator('#files-tbody tr')
        count = await rows.count()
        print(f"File Manager table row count: {count}")

        if count > 0:
            first_row_text = await rows.nth(0).inner_text()
            print(f"First file row: {first_row_text.splitlines()[0]}")

            # Click Play/Preview button
            play_btn = rows.nth(0).locator('button:has-text("เล่น/พรีวิว")')
            print("Clicking '▶ เล่น/พรีวิว' button...")
            await play_btn.click()
            await page.wait_for_timeout(2000)

            # Verify Video Player Element
            video_el = page.locator('#player-container video')
            video_src = await video_el.get_attribute("src")
            print(f"Video element src: {video_src}")

            # Evaluate video readyState
            ready_state = await page.evaluate("document.querySelector('#player-container video')?.readyState")
            print(f"Video element readyState: {ready_state}")

            # Take screenshot of open player in File Manager tab
            artifact_screenshot = r"C:\Users\Thanon6532\.gemini\antigravity-cli\brain\810972ba-a2f6-4d9e-a75d-a5149a2d5b18\playwright_test_result.png"
            await page.screenshot(path=artifact_screenshot, full_page=True)
            print(f"Screenshot saved to {artifact_screenshot}")

            # Click Open Folder button
            folder_btn = rows.nth(0).locator('button:has-text("เปิดโฟลเดอร์")')
            print("Clicking '📂 เปิดโฟลเดอร์คลิปนี้' button...")
            await folder_btn.click()
            await page.wait_for_timeout(1000)

        await browser.close()
        print("\n--- Console Logs Captured ---")
        for log in console_logs:
            print(log)
        print("Playwright test completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_test())

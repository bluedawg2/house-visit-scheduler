"""
Visits the Streamlit app with a real browser.
- If the app is sleeping, clicks the wake-up button and waits for it to boot.
- If the app is already running, the browser visit resets the inactivity timer.
"""

import asyncio
import sys

from playwright.async_api import async_playwright

APP_URL = "https://house-scheduler.streamlit.app/"

# Streamlit Community Cloud sleeping page shows a wake-up button.
# Try multiple text patterns in case the wording changes.
WAKE_SELECTORS = [
    "text=Yes, get this app back up",
    "text=get this app back up",
    "button:has-text('back up')",
    "text=Wake up",
]


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        print(f"Visiting {APP_URL}")
        try:
            await page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc:
            print(f"ERROR: Could not reach app: {exc}")
            await browser.close()
            sys.exit(1)

        # Give the page a moment to render any sleeping-state UI.
        await page.wait_for_timeout(4_000)

        for selector in WAKE_SELECTORS:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=1_500):
                    print(f"App is sleeping — clicking wake button ({selector!r})")
                    await btn.click()
                    print("Waiting up to 60 s for app to start…")
                    await page.wait_for_timeout(60_000)
                    print("Wake complete.")
                    await browser.close()
                    return
            except Exception:
                continue

        print("App is already running — inactivity timer reset.")
        await browser.close()


asyncio.run(main())

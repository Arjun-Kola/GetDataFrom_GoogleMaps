import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def run():
    async with async_playwright() as p:
        # Connect to the existing Chrome instance via CDP
        browser = await p.chromium.connect_over_cdp("http://localhost:9014")

        # Use the default browser context (existing tabs/extensions, etc.)
        context = browser.contexts[0]  # Use the first (main) context
        page = await context.new_page()

        # Open Google Maps with clinic search
        await page.goto("https://www.google.com/maps/search/Dental+Clinic+new+york/")
        await page.wait_for_timeout(8000)  # Wait for results and extension to activate


        # Scroll to load more results
        # for _ in range(5):
        #     await page.evaluate("document.querySelector('div[role=\"main\"]').scrollBy(0, 1000)")
        #     await page.wait_for_timeout(2000)

        # Extract clinic names and addresses
        cards = await page.query_selector_all("//*[@class='qBF1Pd fontHeadlineSmall ']")

        #Basic extraction of text cards (raw content only)
        data = []

        for card in cards:
            try:
                name = await card.inner_text()
            except:
                name = ""
            data.append({"Clinic Name": name})

        # Save to CSV
        df = pd.DataFrame(data)
        df.to_csv("scrapio_restaurants_existing_browser.csv", index=False)
        print("Data saved to scrapio_restaurants_existing_browser.csv")

        # await browser.close()

asyncio.run(run())

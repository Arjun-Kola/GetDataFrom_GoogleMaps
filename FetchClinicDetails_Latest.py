import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def run():
    async with async_playwright() as p:
        # Connect to existing Chrome instance with Scrap.io extension
        browser = await p.chromium.connect_over_cdp("http://localhost:9014")

        context = browser.contexts[0]
        page = await context.new_page()

        stateName = "New York"

        # Open Google Maps search
        await page.goto(f"https://www.google.com/maps/search/Dental+Clinic+{stateName}/")
        await page.wait_for_timeout(5000)  # allow extension to load

        # Keep scrolling until no new clinics load
        prev_count = -1
        while True:
            cards = await page.query_selector_all("//*[@class='qBF1Pd fontHeadlineSmall ']")
            if len(cards) == prev_count:  # stop when no new cards appear
                break
            prev_count = len(cards)
            await page.evaluate("document.querySelector('div[role=feed]').scrollBy(0, 2000)")
            await page.wait_for_timeout(20000)

        print(f"✅ Total Clinics Found: {len(cards)}")

        data = []

        for card in cards:
            row = {}
            try:
                # Clinic Name
                row["Clinic Name"] = await card.inner_text()
            except:
                row["Clinic Name"] = ""

            # Find related Scrap.io items for this clinic
            scrapio_items = await card.query_selector_all(
                "xpath=.//ancestor::div[contains(@class,'bfdHYd')]"
                "/following-sibling::div//*[@class='scrapio-icon-detail scrapio-card-social__item']"
            )
            for item in scrapio_items:
                dtype = await item.get_attribute("data-type")
                durl = await item.get_attribute("data-url")

                if not dtype:
                    continue

                if dtype == "emails":
                    row["Email"] = durl.replace("mailto:", "") if durl else ""
                elif dtype.startswith("phone"):
                    row["Phone"] = durl.replace("tel:", "") if durl else ""
                elif dtype == "website":
                    row["Website"] = durl
                elif dtype == "facebook":
                    row["Facebook"] = durl
                elif dtype == "instagram":
                    row["Instagram"] = durl
                elif dtype == "contact_pages":
                    row["Contact Page"] = durl
                elif dtype == "youtube":
                    row["YouTube"] = durl
                elif dtype == "twitter":
                    row["Twitter"] = durl
                elif dtype == "linkedin":
                    row["LinkedIn"] = durl

            data.append(row)

        # Save results
        df = pd.DataFrame(data)
        df.to_csv(f"scrapio_clinics_{stateName}.csv", index=False, encoding="utf-8-sig")
        print("🎉 Data saved to "+ f"scrapio_clinics_{stateName}.csv")

asyncio.run(run())
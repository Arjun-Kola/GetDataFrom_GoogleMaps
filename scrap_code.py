import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def run():
    async with async_playwright() as p:
        # Connect to existing Chrome instance with Scrap.io extension
        browser = await p.chromium.connect_over_cdp("http://localhost:9014")

        context = browser.contexts[0]
        page = await context.new_page()

        # Open Google Maps search
        await page.goto("https://www.google.com/maps/search/Dental+Clinic+new+york/")
        await page.wait_for_timeout(8000)  # allow extension to load data

        # Get all clinic name elements
        cards = await page.query_selector_all("//*[@class='qBF1Pd fontHeadlineSmall ']")

        data = []

        for card in cards:
            row = {}
            try:
                # Clinic Name
                row["Clinic Name"] = await card.inner_text()
            except:
                row["Clinic Name"] = ""

            # Now find related scrapio items for this clinic
            scrapio_items = await card.query_selector_all(
                                "xpath=.//ancestor::div[@class='bfdHYd Ppzolf OFBs3e  Jv9l1d']"
                                "/following-sibling::div//*[@class='scrapio-icon-detail scrapio-card-social__item']"
                            )
            for item in scrapio_items:
                dtype = await item.get_attribute("data-type")
                durl = await item.get_attribute("data-url")

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

            data.append(row)

        # Save results
        df = pd.DataFrame(data)
        df.to_csv("scrapio_clinics.csv", index=False)
        print("Data saved to scrapio_clinics.csv")

asyncio.run(run())

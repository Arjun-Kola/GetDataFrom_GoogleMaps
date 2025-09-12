import asyncio
from playwright.async_api import async_playwright
import pandas as pd

US_STATES = [
    #"Alabama", "Alaska",
    "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    # "New York", 
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

async def scrape_state(page, stateName):
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
        await page.wait_for_timeout(15000)  # wait for new cards to load

    print(f"✅ {stateName}: Total Clinics Found: {len(cards)}")

    data = []
    for card in cards:
        row = {}
        try:
            row["Clinic Name"] = await card.inner_text()
        except:
            row["Clinic Name"] = ""

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

    # Save results for this state
    df = pd.DataFrame(data)
    filename = f"scrapio_clinics_{stateName.replace(' ', '_')}.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"🎉 Data saved to {filename}")


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9014")
        context = browser.contexts[0]
        page = await context.new_page()

        # Loop through all US states
        for state in US_STATES:
            try:
                await scrape_state(page, state)
            except Exception as e:
                print(f"⚠️ Skipping {state} due to error: {e}")

asyncio.run(run())

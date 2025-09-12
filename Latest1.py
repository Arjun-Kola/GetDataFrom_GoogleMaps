import asyncio
from playwright.async_api import async_playwright
import pandas as pd

# US 50 states 
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]

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

        # 🔑 scroll feed to trigger loading
        await page.evaluate("document.querySelector('div[role=feed]').scrollBy(0, 2000)")
        await page.wait_for_timeout(20000)

    print(f"✅ {stateName}: Total Clinics Found: {len(cards)}")

    # scroll back to top
    await page.evaluate("document.querySelector('div[role=feed]').scrollTo(0, 0)")

    data = []
    

    for i in range(len(cards)):
        base_row = {}

        i = i + 1

        # ---- Click clinic card ----
        # Dynamic XPath
        xpath_str = f"(//*[@class='hfpxzc'])[{i}]"

        print(f"---- Processing clinic {i}/{len(cards)} ----")

        clinicCard = await page.query_selector(f"xpath={xpath_str}")

        if clinicCard:
            await clinicCard.click()
            await page.wait_for_timeout(5000)  # wait for details to load
        else:
            print("⚠️ Could not find clickable element in card")
            continue

        # ---- Clinic Name ----
        try:
            clinicName = await page.query_selector("xpath=//h1[contains(@class,'DUwDvf')]")
            clinicName = await clinicName.inner_text()
            print(f"📌 Clinic: {clinicName}")

            base_row["Clinic Name"] = clinicName
        except:
            base_row["Clinic Name"] = ""

        # ---- Address ----
        try:
            #scroll till address is visible
            await page.wait_for_timeout(3000)
            address_el = await page.query_selector(
                "(//*[@class='Io6YTe fontBodyMedium kR99db fdkmkc '])[1]"
            )

            clinicAddress = await address_el.inner_text()
            print(f"🏠 Address: {clinicAddress}")

            base_row["Address"] = clinicAddress
        except:
            base_row["Address"] = ""

        # ---- Sponsored ----
        try:
            sponsored_el = await page.query_selector("xpath=//span[contains(text(),'Sponsored')]")
            base_row["Sponsored"] = await sponsored_el.inner_text() if sponsored_el else ""
        except:
            base_row["Sponsored"] = ""

        print(f"📌 Clinic: {base_row['Clinic Name']} | Sponsored: {base_row['Sponsored']}")

        # ---- scrapio data ----
        scrapio_items = await page.query_selector_all(
            "xpath=//*[@class='m6QErb DxyBCb kA9KIf dS8AEf XiKgde ']//*[@class='scrapio-card-main__body']//*[@class='scrapio-card-main__rows']/div"
        )

        # Collect multiple values
        emails, phones, websites, facebooks, instagrams, contacts, youtubes, twitters, linkedins = ([] for _ in range(9))

        for item in scrapio_items:

            dtype = await item.get_attribute("data-type")
            print(f"Found scrapio item: {dtype}")

            a_tag = await item.query_selector("a")
            if a_tag:
                href = await a_tag.get_attribute("href")
                print(f"Href: {href}")

            if not dtype:
                continue

            if dtype == "emails":
                emails.append(href.replace("mailto:", "") if href else "")
            elif dtype.startswith("phone"):
                phones.append(href.replace("tel:", "") if href else "")
            elif dtype == "website":
                websites.append(href)
            elif dtype == "facebook":
                facebooks.append(href)
            elif dtype == "instagram":
                instagrams.append(href)
            elif dtype == "contact_pages":
                contacts.append(href)
            elif dtype == "youtube":
                youtubes.append(href)
            elif dtype == "twitter":
                twitters.append(href)
            elif dtype == "linkedin":
                linkedins.append(href)

        # Find max rows needed
        max_len = max(
            len(emails),
            len(phones),
            len(websites),
            len(facebooks),
            len(instagrams),
            len(contacts),
            len(youtubes),
            len(twitters),
            len(linkedins),
            1,
        )

        # Build rows
        for i in range(max_len):
            row = {}
            if i == 0:
                row.update(base_row)  # include clinic info
            else:
                row["Clinic Name"] = ""
                row["Address"] = ""
                row["Sponsored"] = ""

            row["Phone"] = phones[i] if i < len(phones) else (base_row.get("Phone", "") if i == 0 else "")
            row["Email"] = emails[i] if i < len(emails) else ""
            row["Website"] = websites[i] if i < len(websites) else (base_row.get("Website", "") if i == 0 else "")
            row["Facebook"] = facebooks[i] if i < len(facebooks) else ""
            row["Instagram"] = instagrams[i] if i < len(instagrams) else ""
            row["Contact Page"] = contacts[i] if i < len(contacts) else ""
            row["YouTube"] = youtubes[i] if i < len(youtubes) else ""
            row["Twitter"] = twitters[i] if i < len(twitters) else ""
            row["LinkedIn"] = linkedins[i] if i < len(linkedins) else ""

            data.append(row)

        # If no scrapio data at all, at least add one row
        if not scrapio_items:
            data.append(base_row)

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

        for state in US_STATES:
            try:
                await scrape_state(page, state)
            except Exception as e:
                print(f"⚠️ Skipping {state} due to error: {e}")

asyncio.run(run())

import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import os

# US 50 states 
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin",
      "Wyoming"]

async def scrape_state(page, stateName):
    print(f"🚀 Starting to scrape {stateName}...")
    
    # Open Google Maps search
    await page.goto(f"https://www.google.com/maps/search/Dental+Clinic+{stateName}/")
    await page.wait_for_timeout(5000)  # allow extension to load

    prev_count = -1
    no_results_found = False

    # Phase 1: Scroll until card count stops increasing
    while True:
        cards = await page.query_selector_all("//*[@class='qBF1Pd fontHeadlineSmall ']")

        if len(cards) == prev_count:
            break  # move to "No search results" waiting phase
        prev_count = len(cards)

        await page.evaluate("document.querySelector('div[role=feed]').scrollBy(0, 2000)")
        await page.wait_for_timeout(5000)  # 5 seconds wait

    # Phase 2: Wait for "No Search Results" text (max 5 mins)
    MAX_WAIT_NO_RESULTS = 300  # seconds
    WAIT_INTERVAL = 5  # seconds
    waited = 0

    while waited < MAX_WAIT_NO_RESULTS:
        no_results = await page.query_selector("//*[contains(text(), 'reached the end of the list.')]")
        if no_results:
            print("✅ 'You have reached the end of the list.' message detected.")
            no_results_found = True
            break

        await page.wait_for_timeout(WAIT_INTERVAL * 1000)
        waited += WAIT_INTERVAL

    if not no_results_found:
        print("⏳ Timeout: 'No Search Results' message not found within 5 minutes.")

    print(f"✅ {stateName}: Total Clinics Found: {len(cards)}")


    # If no clinics found, save empty file and continue
    if len(cards) == 0:
        df = pd.DataFrame()
        filename = f"scrapio_clinics_{stateName.replace(' ', '_')}.xlsx"
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"⚠️ No clinics found for {stateName}. Empty file saved.")
        return

    # scroll back to top
    await page.evaluate("document.querySelector('div[role=feed]').scrollTo(0, 0)")

    data = []
    
    for i in range(len(cards)):
        base_row = {}

        clinic_index = i + 1

        # ---- Click clinic card ----
        # Dynamic XPath
        xpath_str = f"(//*[@class='hfpxzc'])[{clinic_index}]"

        print(f"---- Processing clinic {clinic_index}/{len(cards)} in {stateName} ----")

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
        for j in range(max_len):
            row = {}
            if j == 0:
                row.update(base_row)  # include clinic info
            else:
                row["Clinic Name"] = ""
                row["Address"] = ""
                row["Sponsored"] = ""

            row["Phone"] = phones[j] if j < len(phones) else (base_row.get("Phone", "") if j == 0 else "")
            row["Email"] = emails[j] if j < len(emails) else ""
            row["Website"] = websites[j] if j < len(websites) else (base_row.get("Website", "") if j == 0 else "")
            row["Facebook"] = facebooks[j] if j < len(facebooks) else ""
            row["Instagram"] = instagrams[j] if j < len(instagrams) else ""
            row["Contact Page"] = contacts[j] if j < len(contacts) else ""
            row["YouTube"] = youtubes[j] if j < len(youtubes) else ""
            row["Twitter"] = twitters[j] if j < len(twitters) else ""
            row["LinkedIn"] = linkedins[j] if j < len(linkedins) else ""

            data.append(row)

        # If no scrapio data at all, at least add one row
        if not scrapio_items:
            data.append(base_row)

    # Save results for this state as Excel file
    # df = pd.DataFrame(data)
    # filename = f"scrapio_clinics_{stateName.replace(' ', '_')}.xlsx"
    # df.to_excel(filename, index=False, engine='openpyxl')

    df = pd.DataFrame(data)

    # 🔥 Remove duplicates by Clinic Name + Address
    df.drop_duplicates(subset=["Clinic Name", "Address"], inplace=True)

    filename = f"scrapio_clinics_{stateName.replace(' ', '_')}.xlsx"
    df.to_excel(filename, index=False, engine='openpyxl')


    print(f"🎉 Data for {stateName} saved to {filename}")
    print(f"📊 Total records saved for {stateName}: {len(cards)}")


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9014")
        context = browser.contexts[0]
        page = await context.new_page()

        completed_states = []
        failed_states = []

        print(f"🌟 Starting scraping process for {len(US_STATES)} states...")
        
        for state_num, state in enumerate(US_STATES, 1):
            print(f"\n{'='*50}")
            print(f"Processing State {state_num}/{len(US_STATES)}: {state}")
            print(f"{'='*50}")
            
            try:
                await scrape_state(page, state)
                completed_states.append(state)
                print(f"✅ Successfully completed {state}")
                
                # Add a small delay between states to avoid being rate limited
                await page.wait_for_timeout(3000)
                
            except Exception as e:
                print(f"⚠️ Error processing {state}: {e}")
                failed_states.append(state)
                continue

        # Summary
        print(f"\n{'='*60}")
        print("SCRAPING SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Successfully completed: {len(completed_states)} states")
        print(f"❌ Failed: {len(failed_states)} states")
        
        if completed_states:
            print(f"\n✅ Completed states: {', '.join(completed_states)}")
        
        if failed_states:
            print(f"\n❌ Failed states: {', '.join(failed_states)}")
            
        print(f"\n📁 Excel files saved for each completed state")

if __name__ == "__main__":
    asyncio.run(run())
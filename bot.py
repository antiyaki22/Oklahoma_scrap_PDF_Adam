import asyncio
import csv
import os
from datetime import datetime
import requests
import subprocess
from playwright.async_api import async_playwright

TARGET_URL = "https://www.okcc.online/index.php"
CSV_FILE = "result.csv"

TABLE_HEADER_SELECTOR = "#rod-table thead tr th"
TABLE_ROW_SELECTOR = "#rodinitialbody tr"
TABLE_CELL_SELECTOR = "td"

def ensure_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "--with-deps"], check=True, shell=True)
    except Exception as e:
        print(f"Error installing Playwright: {e}")

def clear_csv_file():
    if os.path.isfile(CSV_FILE):
        open(CSV_FILE, 'w').close()

async def get_table_headers(page):
    headers = await page.query_selector_all(TABLE_HEADER_SELECTOR)
    header_titles = [await header.text_content() or "N/A" for header in headers]
    header_titles[0] = "PDF"

async def get_pdf_hyperlink(instrument_number: str) -> str:
    url = f"https://www.okcc.online/ajax/auth-new.php"
    data = {
        "s": instrument_number
    }
    headers = {
        "Content-Type": f"application/x-www-form-urlencoded;charset=UTF-8",
        "Referer": f"https://www.okcc.online/index.php",
        "Origin": f"https://www.okcc.online", 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
    
    response = requests.post(url, data=data, headers=headers)

    print("Status Code:", response.status_code)
    print("Response Body:", response.headers)  
    print("Response Content: ", response.content)

    hyperlink = f"https://www.okcc.online/document.php?s={response.text}&d=DOC436S4787&t=rod"
    return hyperlink

async def scrape_table(page):
    table_data = []
    rows = await page.query_selector_all(TABLE_ROW_SELECTOR)

    for row in rows:
        cells = await row.query_selector_all(TABLE_CELL_SELECTOR)
        cell_values = [await cell.text_content() or "N/A" for cell in cells]

        instrument_number = cell_values[1]
        print (f"instrument number: {instrument_number}")

        hyperlink = await get_pdf_hyperlink(instrument_number=instrument_number)
        print (f"hyperlink: {hyperlink}")
        cell_values[0] = hyperlink

        if cell_values:
            table_data.append(cell_values)

    return table_data

def save_to_csv(data, headers, append=True):
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists or not append:
            writer.writerow(headers)

        writer.writerows(data)

async def main():
    clear_csv_file()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto(TARGET_URL, timeout=90000)

        await page.click("div#areastyle > div.col-md-4:first-of-type ul.text-start i.fa-file-magnifying-glass")
        await page.wait_for_selector("input#rodDocTypeTxt")
        await page.fill("input#rodDocTypeTxt", "ml")
        await page.click("text='ML - MECHANIC LIEN'")
        await page.click("#date_range_rod_type")

        ### Date Range Set ###
        today = datetime.today().day
        print (f"today: {today}")
        # three_months_ago = today - relativedelta(months=3)

        await page.click('#drwrapper-rod-type #rodDateFromTxt')
        await asyncio.sleep(1)
        
        for i in range(3):
            await page.click('div.flatpickr-calendar.open .flatpickr-months .flatpickr-prev-month svg')
        dayContainer_from = page.locator('div.flatpickr-calendar.open .flatpickr-innerContainer .dayContainer')
        from_date = dayContainer_from.locator(f"text={today}")
        await from_date.click()

        await page.click('#drwrapper-rod-type #rodToDateTxt')
        await asyncio.sleep(1)

        dayContainer_to = page.locator('div.flatpickr-calendar.open .flatpickr-innerContainer .dayContainer')
        to_date = dayContainer_to.locator(f"text={today}")
        await to_date.click()

        await page.click("#rod-submit-type-search")
        await asyncio.sleep(60)

        num_pages_element = page.locator('#rod_type_table_row > div > div div.rod-pages:first-of-type label.rodMxPgLbl')
        num_pages = await num_pages_element.text_content()

        headers = await get_table_headers(page)

        for i in range(int(num_pages)):

            ### Main Logic ###
            table_data = await scrape_table(page)
            if i == 0:
                save_to_csv(table_data, headers, append=False) 
            else:
                save_to_csv(table_data, None, append=True) 
            ##################

            await page.click('#rod_type_table_row > div > div div.rod-pages:first-of-type i.fa-angle-right')
            i = i + 1

        await browser.close()

ensure_playwright_browsers()
asyncio.run(main())
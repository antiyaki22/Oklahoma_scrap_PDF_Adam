import asyncio
import csv
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
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
    return [await header.text_content() or "N/A" for header in headers]

async def scrape_table(page):
    table_data = []
    rows = await page.query_selector_all(TABLE_ROW_SELECTOR)

    for row in rows:
        cells = await row.query_selector_all(TABLE_CELL_SELECTOR)
        cell_values = [await cell.text_content() or "N/A" for cell in cells]

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
        # await page.click("ul.rcbList li:last-of-type")
        
        await page.wait_for_selector("input#rodDocTypeTxt")
        await page.fill("input#rodDocTypeTxt", "ml")
        await page.click("text='ML - MECHANIC LIEN'")
        await page.click("#date_range_rod_type")

        ### Date Range Set ###
        today = datetime.today()
        three_months_ago = today - relativedelta(months=3)

        await page.fill('#rodDateFromTxt', str(three_months_ago.strftime(f'%m/%d/%Y')))
        await page.fill('#rodToDateTxt', str(today.strftime(f'%m/%d/%Y')))
        ######################

        await page.click("#rod-submit-type-search")
        await asyncio.sleep(30)

        num_pages_element = await page.query_selector('#rod_type_table_row > div > div div.rod-pages:first-of-type label.rodMxPgLbl')
        num_pages = int(num_pages_element.text_content())

        headers = await get_table_headers(page)

        for i in range(num_pages):

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
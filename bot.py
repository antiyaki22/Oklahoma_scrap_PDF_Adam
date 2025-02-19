import asyncio
import csv
import os
import subprocess
from playwright.async_api import async_playwright

TARGET_URL = "https://www.okcc.online/index.php"
CSV_FILE = "result.csv"

def ensure_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "--with-deps"], check=True, shell=True)
    except Exception as e:
        print(f"Error installing Playwright: {e}")

def clear_csv_file():
    if os.path.isfile(CSV_FILE):
        open(CSV_FILE, 'w').close()

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

        await page.click("table tfoot tr.rgPager div.rgAdvPart button.rcbActionButton")
        await page.click("ul.rcbList li:last-of-type")
        await asyncio.sleep(10)

        await browser.close()

ensure_playwright_browsers()
asyncio.run(main())
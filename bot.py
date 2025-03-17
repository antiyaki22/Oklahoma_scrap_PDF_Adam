import asyncio
import csv
import os
from datetime import datetime
import re
import subprocess
from sdk.extract_text_info_from_pdf import ExtractTextInfoFromPDF
import json
import spacy
import zipfile
from playwright.async_api import async_playwright

TARGET_URL = "https://www.okcc.online/index.php"
CSV_FILE = "result.csv"

TABLE_HEADER_SELECTOR = "#rod-table thead tr th"
TABLE_ROW_SELECTOR = "#rodinitialbody tr"
TABLE_CELL_SELECTOR = "td"

nlp = spacy.load("en_core_web_sm")
months = 3

def ensure_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "--with-deps"], check=True, shell=True)
    except Exception as e:
        print(f"Error installing Playwright: {e}")

def clear_downloads_output_folder(download_path, output_path):
    if os.path.exists(download_path):  
        for filename in os.listdir(download_path):
            file_path = os.path.join(download_path, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path) 
                    print(f"Removed: {file_path}")
                elif os.path.isdir(file_path):
                    os.rmdir(file_path) 
                    print(f"Removed directory: {file_path}")
            except Exception as e:
                print(f"Error removing {file_path}: {e}")
    else:
        print(f"Directory {download_path} does not exist.")
    if os.path.exists(output_path):  
        for filename in os.listdir(output_path):
            file_path = os.path.join(output_path, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path) 
                    print(f"Removed: {file_path}")
                elif os.path.isdir(file_path):
                    os.rmdir(file_path) 
                    print(f"Removed directory: {file_path}")
            except Exception as e:
                print(f"Error removing {file_path}: {e}")
    else:
        print(f"Directory {output_path} does not exist.")

def clear_csv_file():
    if os.path.isfile(CSV_FILE):
        open(CSV_FILE, 'w').close()

def extract_dollar_amount(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    patterns = [
        r"of \$\s?([\d,]+\.\d{2})",
        r"\(\$\s?([\d,]+\.\d{2})\)",
        r"\$\s?([\d,]+\.\d{2}) due",
        r"is \$\s?([\d,]+\.\d{2})",
        r"total \$\s?([\d,]+\.\d{2})",
        r"is\$\s?([\d,]+\.\d{2})",
        r"of\$\s?([\d,]+\.\d{2})",
        r"j\$([\d,]+\.\d{2})",
        r"j \$([\d,]+\.\d{2})"
    ]

    all_amounts = []

    for element in data.get("elements", []):
        text = element.get("Text", "")

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        dollar_matches = re.findall(r"\$\s?([\d,]+\.\d{2})", text)  
        all_amounts.extend(dollar_matches)

    if all_amounts:
        return max(all_amounts, key=lambda x: float(x.replace(",", "")))

    return "0"

def extract_full_name(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    full_names = []  
    priority_name = None  

    for element in data.get("elements", []):
        text = element.get("Text", "")
        doc = nlp(text)

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name_parts = ent.text.split()

                if len(name_parts) > 1:  
                    full_names.append(ent.text)
                
                match = re.search(r"against\s+" + re.escape(ent.text), text, re.IGNORECASE)
                if match:
                    priority_name = ent.text  

    return priority_name if priority_name else (full_names[0] if full_names else None)

def extract_phone_number(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    patterns = [
        r"\(\d{3}\)\s\d{3}[-\s]?\d{4}",  
        r"\(\d{3}\)-\d{3}-\d{4}",        
        r"\d{3}-\d{3}-\d{4}"             
    ]

    all_numbers = []

    for element in data.get("elements", []):
        text = element.get("Text", "")

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)  

        number_matches = re.findall(r"\d{10,}", text)  
        all_numbers.extend(number_matches)

    formatted_numbers = [
        f"({num[:3]}) {num[3:6]}-{num[6:10]}" for num in all_numbers if len(num) >= 10
    ]

    if formatted_numbers:
        return max(formatted_numbers, key=len)  

    return "No valid phone number found"

def extract_address(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    patterns = [
        r"\d{1,5}\s\w+(\s\w+)*,\s?[A-Za-z\s]+,\s?[A-Za-z]{2}\s?\d{5}(-\d{4})?",  
        r"\d{1,5}\s\w+(\s\w+)*,\s?[A-Za-z\s]+,\s?\d{5}(-\d{4})?", 
        r"\d{1,5}\s\w+(\s\w+)*,\s?[A-Za-z\s]+", 
        r"[A-Za-z\s]+,\s?[A-Za-z]{2}\s?\d{5}(-\d{4})?",
    ]

    all_addresses = []

    for element in data.get("elements", []):
        text = element.get("Text", "")

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)  

        if any(keyword in text.lower() for keyword in ["street", "st.", "road", "rd.", "avenue", "ave.", "blvd", "lane", "ln.", "drive", "dr.", "city", "state", "zip"]):
            all_addresses.append(text)

    if all_addresses:
        return max(all_addresses, key=len)

    return "No valid address found"  

def extract_info_from_json(json_file_path):
    """Extracts claimant, contractor, owner, and their respective address details accurately from a JSON file."""

    def clean_text(text):
        """Removes non-ASCII characters and extra spaces from text."""
        return re.sub(r'[^\x00-\x7F]+', '', text).strip()

    def extract_address(text):
        """Extracts a street address, city, state, and ZIP code from text."""
        try:
            if not text:
                return None, None, None, None
            text = clean_text(text)
            address_pattern = r'(\d+\s[\w\s.,#-]+?),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5}(-\d{4})?)?'
            match = re.search(address_pattern, text)
            if match:
                return match.group(1), match.group(2), match.group(3), match.group(4) if match.group(4) else None
        except Exception as e:
            print(f"Error extracting address: {e}")
        return None, None, None, None

    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return {}

    claimant, contractor, owner = None, None, None
    claimant_address, owner_address, contractor_address = (None, None, None, None), (None, None, None, None), (None, None, None, None)

    try:
        for element in json_data.get("elements", []):
            text = element.get("Text", "")
            if not text:
                continue  

            text = clean_text(text)

            # Extract claimant (before "claims")
            if "claim" in text.lower() and not claimant:
                claimant_match = re.search(r'([\w\s]+,?\s*Inc)', text, re.IGNORECASE)
                if claimant_match:
                    claimant = claimant_match.group(1).strip()

            # Extract claimant address
            if claimant and not any(claimant_address):
                claimant_address = extract_address(text)

            # Extract contractor (after "claims against")
            contractor_match = re.search(r'claims\s+against\s*([\w\s]+?),', text, re.IGNORECASE)
            if contractor_match and not contractor:
                contractor = contractor_match.group(1).strip()

            # Extract contractor address
            if contractor and not any(contractor_address):
                contractor_address = extract_address(text)

            # Extract owner (after "owned by")
            owner_match = re.search(r'owned by\s*([\w\s,.&-]+?)\s*,\s*([\d\w\s,.-]+)', text, re.IGNORECASE)
            if owner_match:
                owner = owner_match.group(1).strip()
                owner_address = extract_address(owner_match.group(2))  # Extract address after owner name

    except Exception as e:
        print(f"Error processing elements: {e}")

    # If owner's address is still not found, use contractor's address as a fallback
    if not any(owner_address) and any(contractor_address):
        owner_address = contractor_address

    return {
        "Claimant": claimant if claimant else "Not Found",
        "Contractor": contractor if contractor else "Not Found",
        "Owner": owner if owner else "Not Found",
        "Address": owner_address[0] if owner_address[0] else "Not Found",
        "City": owner_address[1] if owner_address[1] else "Not Found",
        "State": owner_address[2] if owner_address[2] else "Not Found",
        "Zipcode": owner_address[3] if owner_address[3] else "Not Found"
    }

def unzip_file(zip_file_path, output_folder):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(output_folder)

def remove_zip_file(zip_file_path):
    try:
        os.remove(zip_file_path)
    except Exception as e:
        print(f"Error removing zip file: {e}")

async def set_table_headers(page) -> list:
    header_titles = []
    header_titles.append("File")
    header_titles.append("Instrument Number")
    header_titles.append("Type")
    header_titles.append("Date Recorded")
    header_titles.append("Book")
    header_titles.append("Page")
    header_titles.append("Claimant")
    header_titles.append("Contractor")
    header_titles.append("Owner")
    header_titles.append("Property Address")
    header_titles.append("Property City")
    header_titles.append("Property State")
    header_titles.append("Property Zip")
    header_titles.append("Dollar Amount")
    header_titles.append("Phone Number")
    return header_titles

async def download_pdf(page, key: str, docid: str):
    pdf_url = None
    def response_handler(response):
        nonlocal pdf_url
        if response.url.startswith("https://www.okcc.online/document.php") and response.headers.get('content-type', '').startswith('application/pdf'):
            pdf_url = response.url

    page.on('response', response_handler)

    await page.evaluate(f'OpenP("{key}", document.body, "{docid}");')
    await asyncio.sleep(5)

    download_path = os.path.join(os.getcwd(), 'downloads')
    os.makedirs(download_path, exist_ok=True)

    response = await page.request.get(pdf_url)

    if response.ok:
        pdf_content = await response.body()
        pdf_path = os.path.join(download_path, f"{docid}.pdf")
        
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)     
    else:
        print("❌ Failed to fetch PDF.")
    
    await page.click(".pdf-close")
    await asyncio.sleep(2)

def remove_watermark(wm_text, inputFile, outputFile):
    from PyPDF4 import PdfFileReader, PdfFileWriter
    from PyPDF4.pdf import ContentStream
    from PyPDF4.generic import TextStringObject, NameObject
    from PyPDF4.utils import b_
    
    with open(inputFile, "rb") as f:
        source = PdfFileReader(f, "rb")
        output = PdfFileWriter()

        for page in range(source.getNumPages()):
            page = source.getPage(page)
            content_object = page["/Contents"].getObject()
            content = ContentStream(content_object, source)

            for operands, operator in content.operations:
                if operator == b_("Tj"):
                    text = operands[0]

                    if isinstance(text, str) and text.startswith(wm_text):
                        operands[0] = TextStringObject('')

            page.__setitem__(NameObject('/Contents'), content)
            output.addPage(page)

        with open(outputFile, "wb") as outputStream:
            output.write(outputStream)

async def process_pdf(docid: str) -> tuple:
    input_pdf_path = f"downloads/{docid}.pdf"
    pdf_filename = os.path.splitext(os.path.basename(input_pdf_path))[0]
    ExtractTextInfoFromPDF(input_pdf_path)
    
    output_folder = "output/ExtractTextInfoFromPDF"
    time_stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    zip_file_path = f"{output_folder}/extract{time_stamp}.zip"
        
    unzip_file(zip_file_path, output_folder)
    remove_zip_file(zip_file_path)

    json_file_path = f"{output_folder}/structuredData.json"
    renamed_json_path = f"{output_folder}/{pdf_filename}.json"

    os.rename(json_file_path, renamed_json_path)    

    info = extract_info_from_json(renamed_json_path)
    dollar_amount = f"${extract_dollar_amount(renamed_json_path)}"
    phone_number = extract_phone_number(renamed_json_path)
    info["Dollar"] = dollar_amount
    info["Phone"] = phone_number

    print (f"info: {info}")
    return info

async def scrape_table(page, headers):
    rows = await page.query_selector_all(TABLE_ROW_SELECTOR)

    for row in rows:
        cells = await row.query_selector_all(TABLE_CELL_SELECTOR)
        cell_values = [((await cell.text_content()) or "").strip() or "N/A" for cell in cells]

        pdf_html_element = await cells[0].query_selector("div > button:first-of-type")
        pdf_html = await pdf_html_element.evaluate("element => element.outerHTML")

        match = re.search(r"OpenP\('([^']+)',this,'([^']+)'\)", str(pdf_html))

        if match:
            instrument_number = match.group(1) 
            doc_id = match.group(2) 
        else:
            print("Document not found!")

        await download_pdf(page, key=instrument_number, docid=doc_id)

        input_path = f"downloads/{doc_id}.pdf"
        temp_output_path = f"downloads/{doc_id}_no_watermark.pdf"

        remove_watermark("UNOFFICIAL", input_path, temp_output_path)

        if os.path.exists(temp_output_path):
            os.remove(input_path) 
            os.rename(temp_output_path, input_path) 
            print(f"Successfully replaced {input_path} with watermark-free version.")
        else:
            print("Error: Watermark removal failed, new file not created.")

        cell_values[0] = f"{doc_id}.pdf"
        print (f"cell values 0: ", cell_values)

        info = await process_pdf(docid=doc_id)
        if cell_values[6] == "N/A":
            cell_values[6] = info["Claimant"]
        if cell_values[7] == "N/A":
            cell_values[7] = info["Contractor"]
        if cell_values[8] == "N/A":
            cell_values[8] = info["Owner"]
        cell_values[9] = info["Address"]
        cell_values.append(info["City"])
        cell_values.append(info["State"])
        cell_values.append(info["Zipcode"])
        cell_values.append(info["Dollar"])
        cell_values.append(info["Phone"])
        print (f"cell values 1: ", cell_values)

        save_to_csv([cell_values], headers=None, append=True)
        await asyncio.sleep(2)

def save_to_csv(data, headers, append=True):
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if headers:
            writer.writerow(headers)
        
        if data:
            writer.writerows(data)

async def main():    
    clear_csv_file()

    download_path = os.path.join(os.getcwd(), 'downloads')
    output_path = os.path.join(os.getcwd(), 'output/ExtractTextInfoFromPDF')
    os.makedirs(download_path, exist_ok=True)
    clear_downloads_output_folder(download_path, output_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto(TARGET_URL, timeout=60000)

        await page.click("div#areastyle > div.col-md-4:first-of-type ul.text-start i.fa-file-magnifying-glass")
        await page.wait_for_selector("input#rodDocTypeTxt")
        await page.fill("input#rodDocTypeTxt", "ml")
        await page.click("text='ML - MECHANIC LIEN'")
        await page.click("#date_range_rod_type")

        today = str(datetime.today().day)

        await page.click('#drwrapper-rod-type #rodDateFromTxt')
        await asyncio.sleep(1)
        
        for i in range(months):
            await page.click('div.flatpickr-calendar.open .flatpickr-months .flatpickr-prev-month svg')
        
        ### From Date Click ###
        dayContainer_from = page.locator('div.flatpickr-calendar.open .flatpickr-innerContainer .dayContainer')
        all_spans = dayContainer_from.locator('span')
        from_date = None

        for index in range(await all_spans.count()):  
            span_element = all_spans.nth(index) 
            text_content = await span_element.inner_text() 
            class_attribute = await span_element.get_attribute("class") 

            if text_content == today and ("prevMonthDay" not in (class_attribute or "")) and ("nextMonthDay" not in (class_attribute or "")):
                from_date = span_element
                break  

        if from_date:
            await from_date.click()
        else:
            print("No valid date found!")
        ###################

        await page.click('#drwrapper-rod-type #rodToDateTxt')
        await asyncio.sleep(1)

        ### To Date Click ###
        dayContainer_to = page.locator('div.flatpickr-calendar.open .flatpickr-innerContainer .dayContainer')
        all_spans = dayContainer_to.locator('span')
        to_date = None

        for index in range(await all_spans.count()):  
            span_element = all_spans.nth(index) 
            text_content = await span_element.inner_text() 
            class_attribute = await span_element.get_attribute("class") 

            if text_content == today and ("prevMonthDay" not in (class_attribute or "")) and ("nextMonthDay" not in (class_attribute or "")):
                to_date = span_element
                break  

        if to_date:
            await to_date.click()
        else:
            print("No valid date found!")
        ###################

        await page.click("#rod-submit-type-search")
        await asyncio.sleep(120)

        num_pages_element = page.locator('#rod_type_table_row > div > div div.rod-pages:first-of-type label.rodMxPgLbl')
        num_pages = await num_pages_element.text_content()

        headers = await set_table_headers(page)
        save_to_csv(data=None, headers=headers, append=True)

        for i in range(int(num_pages)):
            await scrape_table(page, headers=headers)
            await page.click('#rod_type_table_row > div > div div.rod-pages:first-of-type i.fa-angle-right')

        await browser.close()

ensure_playwright_browsers()
asyncio.run(main())
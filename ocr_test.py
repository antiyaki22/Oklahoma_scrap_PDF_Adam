import zipfile
import os
from datetime import datetime
from sdk.extract_text_info_from_pdf import ExtractTextInfoFromPDF
import json
import re

def extract_largest_dollar_amount(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    dollar_values = []
    
    for element in data.get("elements", []):
        text = element.get("Text", "")
        match = re.search(r"\$\s?([\d,]+\.?\d*)", text)
        if match:
            amount = float(match.group(1).replace(',', ''))
            dollar_values.append(amount)

    return max(dollar_values, default=None)

def unzip_file(zip_file_path, output_folder):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(output_folder)

def remove_zip_file(zip_file_path):
    try:
        os.remove(zip_file_path)
    except Exception as e:
        print(f"Error removing zip file: {e}")

if __name__ == "__main__":
    input_pdf_path = "downloads/ocr_test.pdf"
    pdf_filename = os.path.splitext(os.path.basename(input_pdf_path))[0]
    ExtractTextInfoFromPDF(input_pdf_path)
    
    output_folder = "output/ExtractTextInfoFromPDF"
    time_stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    zip_file_path = f"{output_folder}/extract{time_stamp}.zip"
        
    unzip_file(zip_file_path, output_folder)
    remove_zip_file(zip_file_path)

    output_folder = "output/ExtractTextInfoFromPDF"    

    json_file_path = f"{output_folder}/structuredData.json"
    renamed_json_path = f"{output_folder}/{pdf_filename}.json"

    os.rename(json_file_path, renamed_json_path)    
    largest_value = extract_largest_dollar_amount(renamed_json_path)
    
    if largest_value is not None:
        print(f"Largest dollar amount: ${largest_value}")
    else:
        print("No dollar amounts found.")

import zipfile
import os
from datetime import datetime
from sdk.extract_text_info_from_pdf import ExtractTextInfoFromPDF
import json
import re
import fitz
from PIL import Image
from io import BytesIO

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

if __name__ == "__main__":
    input_pdf_path = "downloads/ocr_test.pdf"
    pdf_filename = os.path.splitext(os.path.basename(input_pdf_path))[0]

    remove_watermark("UNOFFICIAL", "downloads/ocr_test.pdf", "again.pdf")

    # ExtractTextInfoFromPDF(input_pdf_path)
    
    # output_folder = "output/ExtractTextInfoFromPDF"
    # time_stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    # zip_file_path = f"{output_folder}/extract{time_stamp}.zip"
        
    # unzip_file(zip_file_path, output_folder)
    # remove_zip_file(zip_file_path)

    # output_folder = "output/ExtractTextInfoFromPDF"    

    # json_file_path = f"{output_folder}/structuredData.json"
    # renamed_json_path = f"{output_folder}/{pdf_filename}.json"

    # os.rename(json_file_path, renamed_json_path)    
    # largest_value = extract_largest_dollar_amount(renamed_json_path)
    
    # if largest_value is not None:
    #     print(f"Largest dollar amount: ${largest_value}")
    # else:
    #     print("No dollar amounts found.")

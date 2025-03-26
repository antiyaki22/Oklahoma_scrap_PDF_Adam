import zipfile
import os
from datetime import datetime
from sdk.extract_text_info_from_pdf import ExtractTextInfoFromPDF
from sdk.extract_text_info_with_char_bounds_from_pdf import ExtractTextInfoWithCharBoundsFromPDF
import json
import re
import fitz
from PIL import Image
from io import BytesIO
import usaddress

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

def extract_address(text):
    try:
        if not text:
            return None, None, None, None

        def clean_text(text):
            return re.sub(r'[^\x00-\x7F]+', ' ', text).strip()

        text = clean_text(text)

        # Extract address using usaddress
        try:
            tagged_address, address_type = usaddress.tag(text)
        except usaddress.RepeatedLabelError:
            tagged_address = {}

        address_parts = []
        city, state, zipcode = None, None, None

        # Extract components from tagged address using usaddress
        for key, value in tagged_address.items():
            if key == "PlaceName" and not city:
                city = value
            elif key == "StateName" and not state:
                state = value
            elif key == "ZipCode" and not zipcode:
                zipcode = value
            elif key in ["AddressNumber", "StreetName", "StreetNamePreType", "StreetNamePostType",
                         "OccupancyType", "OccupancyIdentifier", "BuildingName", "SubaddressType",
                         "SubaddressIdentifier", "USPSBoxType", "USPSBoxID"]:
                if value not in address_parts:
                    address_parts.append(value)

        address = " ".join(address_parts).strip()

        # Check if address is still empty or incomplete
        if not address or len(address.split()) > 8 or not city or not state or not zipcode:
            # Use regex as a fallback to extract address, city, state, and zip
            regex = r'(\d+\s[\w\s\.,#-]+),\s*([A-Za-z\s]+),\s*([A-Za-z]{2,})\s*(\d{5})?'
            matches = re.findall(regex, text)

            if matches:
                extracted_address, extracted_city, extracted_state, extracted_zip = matches[-1]
                address = extracted_address.strip()
                city = extracted_city.strip()
                state = extracted_state.strip()
                zipcode = extracted_zip.strip() if extracted_zip else zipcode

        # If still empty, use a broader regex to find potential address, city, state, and zip
        if not address or not city or not state or not zipcode:
            # Broader address regex with more lenient matching for address format
            structured_regex = r'(\d+\s[\w\s\.,#-]+)\s*,\s*([\w\s]+),\s*([\w]+),\s*(\d{5})'
            structured_match = re.search(structured_regex, text)

            if structured_match:
                address, city, state, zipcode = structured_match.groups()

        # Handle PO Box cases
        po_box_regex = r'(PO Box \d+),\s*([A-Za-z\s]+),\s*([A-Za-z]{2,})\s*(\d{5})?'
        po_box_match = re.search(po_box_regex, text, re.IGNORECASE)
        if po_box_match:
            address, city, state, zipcode = po_box_match.groups()

        # Handle address variations like street number, city, state
        address_fallback_regex = r'(\d+\s[\w\s\.,#-]+),\s*([\w\s]+),\s*([\w]+),\s*(\d{5})'
        address_fallback_match = re.search(address_fallback_regex, text)
        if address_fallback_match:
            address, city, state, zipcode = address_fallback_match.groups()

        # Ensure state is a proper abbreviation (convert full name if needed)
        state_abbreviations = {
            "Oklahoma": "OK",
            "Texas": "TX",
            "California": "CA",
            "Idaho": "ID",
            "Louisiana": "LA",
            # Add more states as needed
        }

        if state in state_abbreviations:
            state = state_abbreviations[state]

        return address, city, state, zipcode

    except Exception as e:
        print(f"Error in extract_address: {e}")
        return None, None, None, None
    
if __name__ == "__main__":
    # input_pdf_path = "downloads/ocr_test.pdf"
    # pdf_filename = os.path.splitext(os.path.basename(input_pdf_path))[0]

    # # remove_watermark("UNOFFICIAL", "downloads/ocr_test.pdf", "again.pdf")

    # # ExtractTextInfoFromPDF(input_pdf_path)
    # ExtractTextInfoWithCharBoundsFromPDF(input_pdf_path)
    
    # output_folder = "output/ExtractTextInfoWithCharBoundsFromPDF"
    # time_stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    # zip_file_path = f"{output_folder}/extract{time_stamp}.zip"
        
    # unzip_file(zip_file_path, output_folder)
    # remove_zip_file(zip_file_path)

    # json_file_path = f"{output_folder}/structuredData.json"
    # renamed_json_path = f"{output_folder}/{pdf_filename}.json"

    # os.rename(json_file_path, renamed_json_path)    
    # largest_value = extract_largest_dollar_amount(renamed_json_path)
    
    # if largest_value is not None:
    #     print(f"Largest dollar amount: ${largest_value}")
    # else:
    #     print("No dollar amounts found.")
    text = "owner: 2025031801037225 B: 16035 P: 34  03/18/2025 09:05:26 AM Pgs: 7  Fee: $47.20  Maressa Treat, County Clerk  Oklahoma County -State of Oklahoma  Prepared and Submitted For Recording By: BLACKMON MOORING OF OKC, LLC Signed by Erin Hildebrand, as agent of BLACKMON MOORING OF OKC, LLC  Please Return To Submitter At BLACKMON  SPACE ABOVE FOR RECORDER'S USE  MOORING OF OKC, LLC  1101 Enterprise Ave, Ste 1  OkJahoma City, Oklahoma 73128  MECHANIC'S OR MATERIALMAN'S LIEN STATEMENT  State of Oklahoma I County of Oklahoma County  Pursuant to Okla. Stat. tit. 42, § 141  ML#  LV Reference ID: 9BG3877YMR2K  Claimant  BLACKMON MOORING OF OKC, LLC  1101 Enterprise Ave, Ste 1  OkJahoma City, Oklahoma 73128  (817) 810-5686  Property Owner I  O  White, Michael  1125 Sw 78th Ter  Oklahoma City, OK 73139  Amount of Claim  $9,811.92  Itemized Invoice or Statement Supporting Above Amount As Follows or Attached Hereto:  General Statement of kind of work done and/or materials furnished (Services):  Materials and Labor for Reconstruction­Structural Damage  Date of Contract:  December 07, 2024  LEVELSET 1121 JOSEPHINE ST NEW ORLEANS, LA 70130  Last Date Labor and/or Materials  7/477°  Furnished:  January 31, 2025  IMPORTANT INFORMATION ON FOLLOWING PAGE  Ł  The Services were performed in construction of improvements at the following described Property:  State of Oklahoma  County: Oklahoma County  1125  SW 78th Terrace  Oklahoma City, Oklahoma 73139  Legal Property Description:  Please see attached Exhibit A. Tax ID: 109891520  Know all persons by these presents:  1.  That the above-identified and undersigned Claimant, BLACKMON MOORING OF OKC, LLC, has and claims a mechanic's and materialman's lien upon the property situated in the State of Oklahoma, county of Oklahoma County, and described above in this statement as the Property, together with the structures, buildings, improvements and appurtenances thereon and thereto.  2.  That the land, buildings, appurtenances and improvements are"
    address, city, state, zip = extract_address(text)
    print (address, city, state, zip)

import zipfile
import os
from datetime import datetime
from sdk.extract_text_info_from_pdf import ExtractTextInfoFromPDF
from sdk.extract_text_info_with_char_bounds_from_pdf import ExtractTextInfoWithCharBoundsFromPDF
import json
import re
from PIL import Image
from io import BytesIO
import usaddress
import spacy
from spacy.matcher import Matcher

nlp = spacy.load("en_core_web_sm")

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
        text = re.sub(r'\s+', ' ', text)

        print("Cleaned Text:", text)  

        try:
            parsed_address = usaddress.parse(text)
            print("usaddress.parse output:", parsed_address) 

            address_number = None
            street_name = []
            street_name_post_type = None
            place_name = None
            state_name = None
            zip_code = None

            for component, label in parsed_address:
                if label == "AddressNumber" and not address_number:
                    address_number = component
                elif label == "StreetName" and not street_name:
                    street_name.append(component)
                elif label == "StreetNamePostType" and not street_name_post_type:
                    street_name_post_type = component
                elif label == "PlaceName" and not place_name:
                    place_name = component.strip(",")
                elif label == "StateName" and not state_name:
                    state_name = component
                elif label == "ZipCode" and not zip_code:
                    zip_code = component

            if address_number and street_name and street_name_post_type:
                best_address = " ".join([address_number] + street_name + [street_name_post_type])
            elif street_name:
                best_address = " ".join([address_number] + street_name) if address_number else " ".join(street_name)

            best_city = place_name
            best_state = state_name
            best_zipcode = zip_code

            print("Final Address:", best_address, best_city, best_state, best_zipcode)

        except usaddress.RepeatedLabelError:
            print("usaddress.parse failed")

        return best_address, best_city, best_state, best_zipcode

    except Exception as e:
        print(f"Error in extract_address: {e}")
        return None, None, None, None
    
def get_merged_text(file_path: str) -> str:
    with open(file_path, 'r') as file:
        json_data = json.load(file)

    merged_text = ""
    for element in json_data.get("elements", []):
        if "Text" in element:
            merged_text += element["Text"] + " "
    
    return merged_text.strip()

def extract_company_name(text):
    doc = nlp(text)
    
    matcher = Matcher(nlp.vocab)
    
    company_patterns = [
        [{"LOWER": {"in": ["inc", "llc", "ltd", "corporation", "group", "enterprises", "holdings", "company"]}}]
    ]
    
    matcher.add("CompanyName", company_patterns)
    
    matches = matcher(doc)
    
    company_names = []
    
    for match_id, start, end in matches:
        span = doc[start:end]
        company_name = span.text.strip()
        
        if len(company_name.split()) > 1:
            company_names.append(company_name)
    
    company_names = [name for name in company_names if not re.search(r'\d{1,5}\s\w+(\s\w+)*', name)]
    
    if company_names:
        company_names.sort(key=len, reverse=True)
        return company_names[0]
    
    return None

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

    # text = "PAYDAR PROPERTIES LLC, 3132 ASH GROVE RD EDMOND, OK 73003  And described as follows to wit: (LEGAL DESCRIPTION)  THE TRAILS SOUTH 3RD ADON Block 006 Lot 004  as  of $ 800.00  In said County and State; that the sum is just due and unpaid, and I have claimed a lien upon said building and upon the said premises on which the same is situated, to the amount above set forth, according to the laws of the State of Oklahoma. Dated this 25 _day of MARCH .2025  Ł  2025032501040838 B: 16042 P: 803 03/25/202511:54 AM Page 2 of 2  Note: Attach itemized statement  STATE OF OKLAHOMA  )  coumv or (DK.\0 h.61a ) )  ss  ŁŁŁŁŁŁŁŁŁŁ ŁŁŁŁ ŁŁŁ  , of lawful age, being first duly sworn upon oath, says: That he/she is the claimant mentioned in the foregoing Statement of Mechanic's Lien; that he/she had read said statement and knows the contents thereof; that the name of the owner. name of the contractor. the name of the claimant, the description of the property upon which the lien is claimed. and the items of the account as therein set forth, are just, true, and correct.  susscnbed and »mom w before me  My commission expires:  Commission #:  NOTARY PUBLIC"
    # text = "Lone Oak Pointe Homeowners Association (Lone Pointe), the owner of the property and whose last known addresses are c/o David Forgey, RSA, 4801 Gaillardia Parkway, Suite 170, Oklahoma City, OK 73142 and c/o Beverly Botchlet, 12101 N. MacArthur Box 158, Oklahoma City, OK 73162, being the owner of the land, building(s), appurtenances and improvements and against whom Van Eaton claims a lien;  That the amount of the lien claimed against the property owner, Lone Pointe totals Eleven Thousand Nine Hundred Eighty-Five Dollars and Sixty-Eight Cents ($11,985.68) and interest at the rate allowed by law. Copy of Van Eaton's itemized invoice is attached as Exhibit A: 2  That the original contractor is American Asphalt & Concrete, LLC American, whose last known address is 6117 Lytle Dr., Oklahoma City, OK 73127;  That beginning on December 12, 2024, Van Eaton furnished material to American, used op or for the land, building(s), appurtenances and improvements located at Lone Pointe Addition, Edmond, OK;  That Van Eaton furnished material used, on or for the land, building(s), appurtenances and improvements as fully described hereafter: ready mix concrete;  That the date upon which the material used on Lone Pointe Addition, Edmond; OK was last furnished was December 12, 2024; and that the lien statement filed on March 11, 2025 in Book 16027 at Page 1880 was filed with the county clerk within ninety (90) days of said date.  That Van Eaton has a claim against American in the amount of Eleven Thousand Nine Hundred Eighty-Five Dollars and Sixty-Eight Cents ($11,985.68), interest at the rate of 1.5% per month, and attorney fees in the amount of Three Hundred Eighty-Two Dollars and 50/100 ($382.50) pursuant to that certain Van Eaton Credit Application dated April 11, 2023. I  That the said amount is just, due, and unpaid, and that Van Eaton claims and has a lien upon the land, building(s), appurtenances and improvements described above, and against Lone Oak in the amount of Eleven Thousand Nine Hundred Eighty-Five Dollars and Sixty-Eight Cents ($11,985.68), and interest at the rate allowed by law, according to the laws of the State of Oklahoma.  DATED this Zlet!-day of March, 2025.  VAN EATON READY MIX, INC.  e Witt/Authorized Representative \  J  STATE OF OKLAHOMA ) ) ss. COUNTY OF POTTAWATOMIE )  That I Jeanne Witt, being of lawful age and first duly sworn under oath, deposes and states: That I am the Authorized Representative of the claimant, Van Eaton Ready Mix, Inc. mentioned in the foregoing 'Amended Mechanic's or Materialman's Lien Statement; that I have read said lien statement and know the contents thereof; that the amount claimed, the name of the owner, the name of the contractor, the description of the property upon which the lien is claimed, and the information set forth in the itemized and described list and the attached Exhibit is just, true and correct.  VAN EATON READY MIX, INC.  Ł e Witt/Authorized Representative  STATE OF OKLAHOMA  )  ) ss.  COUNTYOFPOTIAWATOMIE )  Subscribed and sworn to _before me this  /  Ł=S·Ł Notary Public  THIS LIEN STATEMENT PREPARED BY:  Bruce F. Klein, OBA #11389  BRUCE F. KLEIN, PLLC  222 N.W. 13th Street  Oklahoma City, Oklahoma 73103  Telephone: (405) 606-4448  Facsimile: (405) 523-2108  ATTORNEY FOR VAN EATON READY MIX, INC.  SHAWN HATCH Notary Public, State of Oklahoma Commission # 09007371 My Commission Expires 08-31-2025  \  Please send a copy of the lien to the following:  Łmerican Asphalt&. Concrete & Concrete LLC  6117 Lytle Dr  Oklahoma City, OK 73127  And  6one Oak Pointe Homeowners Associatiori  c/o David Forgey, RSA  4801 Gaillardia Parkway, Suite 170  Oklahoma City, OK 73142  And  @Lone Oak Pointe Homeowners Association  c/o Beverly Botchlet  12101 N MacArthur  Box 158  Oklahoma City, OK 73162  /  Ł  o ..nu e. VANEATON AEA□Y MIx Phone (405) 214-7450 Fax # (405) 214-7448  I Bill To  .as a.necesa i AMERICAN ASPHALT &( Ł  6117 LYTLE DR  OKLAHOMA CITY, OK 73127  Ship To  11  j»»meses  [OKLAHOMA CITY. OK  Invoice  Date  Invoice #  12/12/2024]  235693  Remit to:  Van Eaton Ready Mix, Inc PO Box 1058  Shawnee, OK 74802  P.O. No.  Terms  POINTE OAK CIR  Ner 30  Qty  Ticket#  Item Description  Rate  Amount  10  164727  3500 PSI CONCRETE W/ AIR  165.00  1,650.00  10  164727  STRAIGHT CEMENT POWDER  6.00  60.00  10  164727  FIBER PER YARD  6.00  60.00  10  164727  HOT WATER  5.00  50.00  10  164727  MIDRANGE  3.75  37.50  10  164727  NON-CAC ACCELERATOR 2  9.50  95.00  10  164729  I  3500 PSI CONCRETE W/ AIR  165.00  1,650.00  10  164729  STRAIGHT CEMENT POWDER  6.00  60.00  10  164729  FIBER PER YARD  6.00  60.00  10  164729  HOT WATER  5.00  50.00  10  164729  MIDRANGE  3.75  37.50  10  164729  NON-CAC ACCELERATOR 2  9.50  95.00  10  164736  3500 PSI CONCRETE W/ AIR  165.00  1,650.00  10  164736  STRAIGHT CEMENT POWDER  6.00  60.00  10  164736  FIBER PER YARD  6.00  60.00  10  164736  HOT WATER  5.00  50.00  10  164736  MIDRANGE  3.75  37.50  10  164736  NON-CAC ACCELERATOR 2  9.50  95.00  10  164745  3500 PSI CONCRETE W/ AIR  165.00  1,650.00  10  164745  STRAIGHT CEMENT POWDER  6.00  60.00  You can now pay your bill online! Go to our website, www.vaneatonreadymix.com and click Customer Service --then the blue button at the bottom of the screen. Please also email a payment stub to jeanne@vaneatonreadymix.com.  Page 1  Subtotal  Sales Tax (8.625%)  S Balance Due Ł EXHIBIT  : A  / 0 5323: vN EATON A'EADY MIX Phone # (405) 214-7450 Fax # (405) 214-7448 Invoice Date Invoice # 12/12/2024] 235693 Ł ax. Ł Ł ŁŁ Ł Ł scar scat 1 IE3RES 6117 LYTLEDR I OKLAHOMA CITY, OK 73127 Remit to: VanEaton Ready Mix, Inc PO Box 1058 Shawnee, OK 74802 Qty 10 10 10 1 10 10 10 10 10 10 10 6 6 6 6 6 6 Ticket # 164745 164745 164745 164745 164745 164746 164746 164746 164746 164746 164746 164760 164760 164760 164760 164760 164760 Ł Item Description FIBER PER YARD HOT WATER. MIDRANGE WASHOUT BAG NON-CAC ACCELERATOR 2 3500 PSI CONCRETE W/ AIR iv STRAIGHT CEMENT POWDER FIBER PER YARD HOT WATER MIDRANGE NON-CAC ACCELERATOR 2 3500 PSI CONCRETE W/ AIR STRAIGHT CEMENT POWDER • Ł Ł FIBER PER YARD HOT WATER MIDRANGE NON-CAC ACCELERATOR 2 -PAVING-P.O. No. Terms POINTE OAK CIR Net 30 Rate Amount 6,00 5.00 3.75 100.00 9.50 165.00 6.00l 6.00 5.00 3.75 9.50 165.00 6.00 6.00 5.00 3.75 9.50 60.00 50.00 37.50 100.00 95.00 1,650.00 60.00 60.00 50.00 37.50 95.00 990.00 36.00 36.00 30.00 22.50 57.00 You can now pay your bill online! Go to our website, SubtotalŁ$11,034.00 www.vaneatonreadymix.com and click -then the blue Sales Tax (8.625%) $951.68 button at the bottom of the screen. Please also email a Ł payment stub to jeanne@vaneatonreadymix.com. Balance Due $11,985.68 Page 2 1"
    # text = "yHomsey Dini Massad, 14400 Coles Rd., Edmond, Oklahoma 73013 (Collectively, the Owner) located at 1440 Coles rd., Edmond, Oklahoma 73013 and the with the legal description of upon the following property, situated in Oklahoma County, Oklahoma, in the city or town of Edmond, to wit:  Block 1, Lot 7. NORTHWESTERN ESTATES Addition to City of Oklahoma City, Oklahoma County, State of Oklahoma (NORTHWESTERN ESTATES 001 000 ALL OF LOT 7 & PT OF LOT 6 BEG AT NW/C LT 6] NELY267.02FT SELY30FT SWLY270.29FT TO BEG  This Lien is claimed, separately and severally, as to both the home and improvements thereon, and the said real property. The Claimant and Homsey Dini Massad (Owner) entered into a agreement on the 4th day of September, 2024 whereby the Claimant provided the following labor, services, material, and/or equipment at the Property (the Work) Services as Construction Management as Advisors, work was performed on a cost plus 10% basis, for the total amount of $113,820.85.  Page 1 of 2  2025032501040826 B: 16042 P: 778 03/25/202511:14 AM Page 2 of 2  The first day of Work on the Property by the Claimant was September 23, 2024. The last day of Work on the Property by the Claimant was on February 25, 2025 (the Completion Date)  As of the Effective Date, the Claimant has received payment in the amount $0.00 and concessions by the Claimant of $0.00.  The Owner has failed to pay the Balance Due despite demands and requests for payment. Accordingly, the Claimant declares the claim amount of $113,820.85 is justly due to the Clamant.  The Claimant declares that the contents of this Lien are true and correct to the best their knowledge. Subscribed and sworn to as of the Effective Date.  Clark Construction Inc (Claimant)  Ł Ł Ł 1015 E. Grand Blvd. Oklahoma City, OK 73129.  NOTARY ACKNOWLEDGMENT  State of Oklahoma  County of Oklahoma  This instrument was acknowledged before me on the 25 day of March, 2025, by James Allen Clark, Clark Construction Inc., who is personally known to me satisfactorily proven to m Ł Ł Ł Ł name Ł is subscribed to the within instrument.  NotaryPublicŁ// Print name: X@AEY AI My commission expires: Y&Y,ZZZ  ŁŁŁŁ Ł Ł UŁHŁ7, s"  "ŁŁv ii2Ł seŁe'he s'Ł6€ -• C • -Ł ; ommission # : Ł Ł : 24004583 ; Ł -• Ł e Ł Ł % c:Ł Ł Ł Ł o •°: Ł Ł Ł %ŁŁŁŁ7es 7sir3s Ł Poi:S ŁŁ Ł MILŁŁAS  Page 2 of2"
    # text = "Burlington Crossing, LLC, an Oklahoma limited liability company, 9204 N. Kelley Avenue, Oklahoma City, OK 73131 and having the legal description as shown on the attached Exhibit ; that the said sum is just, due and unpaid, and Sunstate Equipment Co., claims a lien upon said buildings and upon the said premises on which the same is situated, to the amount of $23,443.00 as above set forth, according to the laws of the State of Oklahoma.  Dated this 257day of le/ .202s. Ł  Reynolds, Ridings, Vogt & Robertson  101  Park Avenue, Suite 1010  Oklahoma City, OK 73102  VERIFICATION  STATE OF OKLAHOMA  ) ss.  COUNTY OF OKLAHOMA)  James Vogt, of lawful age, being first duly sworn, upon oath says: That he is the Attorney for Sunstate Equipment Co., and authorized to execute this verification; that he has read this statement and knows the contents thereof; that the name of the owner, the name of the claimant, the description of the property upon which the lien is claimed, and the items of the account as therein set forth, are just, true, correct and unpaid and claimant has complied with the provisions 0f 42 O.S.  §142.6.  , 2025.  Mail Notices to:  Burlington Crossing, LLC, an Oklahoma limited liability company  9204 N. Kelley Avenue  Oklahoma City, OK 73131  Kalka Steel Erectors, LLC  348928 E 910 Road  Chandler, OK 74834  2025032501041113 B: 16043 P: 490 03/25/2025 04:23 PM Page 3 of 5 2024042601053574 B: 15736 P: 1482 04/26/202412:06 PM Page 13 of 13  Exhibit   A tract of land being a part of the Northwest Quarter (NW/4) of Section Four (4 Twelve (12) North, Range Three (3) West of the Indian Meridian, Oklahoma Ci Oklahoma, and being a portion of Lot Twenty-five A (25A) in Block Five (5) of according to the Plat recorded in Book PL77, Page 13, being more partic BEGINNING at the Northeast (NE) Corner of said Lot 25A; THENCE Sout Ł the East line of said Lot 25A, a distance of 318.96 feet; THENCE South East line, a distance of 90.00 feet to a point on the West line of said Lot 11 West, along and with said West line, a distance of 318.96 feet to the Nort Ł Lot 25A; THENCE North 63°38[31 East, along and with the North li feet to the POINT OF BEGINNING. Ł Ł Ith  3/25/25  C=P2P D=Dispute S=Inv Sum 7=Fax 8=LienWvr 9=WriteOff E=Email  14:04:28 Customer Invoice Inquiry Sys: SUNSTATE status: H Total $: 67,576.32 Location Search Cmp: SS Loe: PHX Cust #: 129057 KALKA STEEL ERECTORS, LLC Phone: 405-240-4608 Email: Y Select-Open: Y Paid: N Options: 2=LateChg 3=Pmt/Adj 5=Display 6=Print  •□ � � '''*' ' "" � � 80,3, NW...............�.� Op Invoice # Type ST Inv Date Balance Loc W Job Location_ 12886725-004 RETURN OP 12/19/24 204.26 OKC 803 NW 72ND ST OKLAHOMA C  23443.08  <----Total  Bottom F3=Exit F4=Search Fl1=More F13=Pmt hst F15=Sales hst F22=Aging F24=More Make selections.  3/25/25 14:04:28 customer Invoice Inquiry Sys: SUNSTATE status: H Total $: 67,576.32 Location search Cmp: ss Loe: PHX Cust #: 129057 KALKA STEEL ERECTORS, LLC Phone: 405-240-4608 Email: Y Select-Open: Y Paid: N Options: 2=LateChg 3=Pmt/Adj 5=Display 6=Print  C=P2P  S=Inv, Sum 7=Fax 8=LienWvr 9=WriteOff E=Email  D=Dispute  • Ł Ł '''' '''' ' Ł Ł 8,0,3, NWŁ..............Ł Ł  Op  Invoice #  Type  ST  Inv Date  Balance  Loc W  Job  Location  _  12886252-001  BILLED  OP  11/18/24  3751.36  OKC  803  NW 72ND ST  OKLAHOMA C  - 12886252-002  BILLED  OP  12/16/24  3753.28  OKC  803  NW 72ND ST  OKLAHOMA C  - 12886252-003  RETURN  OP  12/23/24  43.41  OKC  803  NW 72ND ST  OKLAHOMA C  - 12886353-001  BILLED  OP  11/18/24  2726.49  OKC  803  NW 72ND ST  OKLAHOMA C  - 12886353-002  BILLED  OP  12/16/24  2390.97  OKC  803  NW 72ND ST  OKLAHOMA C  12886353-003  RETURN  OP  1/02/25  2243.81  OKC  803  NW 72ND ST  OKLAHOMA C  - 12886354-001  BILLED  OP  11/18/24  759.66  OKC  803  NW 72ND ST  OKLAHOMA C  _  12886354-002  BILLED  OP  12/16/24  609.96  OKC  803  NW 72ND ST  OKLAHOMA C  - 12886354-003  RETURN  OP  12/23/24  150.00  OKC  803  NW 72ND ST  OKLAHOMA C  _  - 12886363-001  BILLED  OP  11/18/24,  759.66  OKC  803  NW 72ND ST  OKLAHOMA C  12886363-002  BILLED  OP  12/16/24  609.96  OKC  803  NW 72ND ST  OKLAHOMA C  - 12886363-003  RETURN  OP  1/02/25  759.45  OKC  803  NW 72ND ST  OKLAHOMA C  _  - 12886725-002  BILLED  OP  11/18/24  2414.83  OKC  803  NW 72ND ST  OKLAHOMA C  _  12886725-003  BILLED  OP  12/16/24  2265.98  OKC  803  NW 72ND ST  OKLAHOMA C  More...  F3=Exit F4=Search F11=More F13=Pmt hst F15=Sales hst F22=Aging F24=More Make selections."
    # text = "owner: 2025031801037225 B: 16035 P: 34  03/18/2025 09:05:26 AM Pgs: 7  Fee: $47.20  Maressa Treat, County Clerk  Oklahoma County -State of Oklahoma  Prepared and Submitted For Recording By: BLACKMON MOORING OF OKC, LLC Signed by Erin Hildebrand, as agent of BLACKMON MOORING OF OKC, LLC  Please Return To Submitter At BLACKMON  SPACE ABOVE FOR RECORDER'S USE  MOORING OF OKC, LLC  1101 Enterprise Ave, Ste 1  OkJahoma City, Oklahoma 73128  MECHANIC'S OR MATERIALMAN'S LIEN STATEMENT  State of Oklahoma I County of Oklahoma County  Pursuant to Okla. Stat. tit. 42, § 141  ML#  LV Reference ID: 9BG3877YMR2K  Claimant  BLACKMON MOORING OF OKC, LLC  1101 Enterprise Ave, Ste 1  OkJahoma City, Oklahoma 73128  (817) 810-5686  Property Owner I  O  White, Michael  1125 Sw 78th Ter  Oklahoma City, OK 73139  Amount of Claim  $9,811.92  Itemized Invoice or Statement Supporting Above Amount As Follows or Attached Hereto:  General Statement of kind of work done and/or materials furnished (Services):  Materials and Labor for Reconstruction­Structural Damage  Date of Contract:  December 07, 2024  LEVELSET 1121 JOSEPHINE ST NEW ORLEANS, LA 70130  Last Date Labor and/or Materials  7/477°  Furnished:  January 31, 2025  IMPORTANT INFORMATION ON FOLLOWING PAGE  Ł  The Services were performed in construction of improvements at the following described Property:  State of Oklahoma  County: Oklahoma County  1125  SW 78th Terrace  Oklahoma City, Oklahoma 73139  Legal Property Description:  Please see attached Exhibit A. Tax ID: 109891520  Know all persons by these presents:  1.  That the above-identified and undersigned Claimant, BLACKMON MOORING OF OKC, LLC, has and claims a mechanic's and materialman's lien upon the property situated in the State of Oklahoma, county of Oklahoma County, and described above in this statement as the Property, together with the structures, buildings, improvements and appurtenances thereon and thereto.  2.  That the land, buildings, appurtenances and improvements are"
    
    # text = get_merged_text("test.json")
    # print (text)
    # address, city, state, zip = extract_address(text)

    text = "HERITAGE LANDSCAPE SUPPLY GROUP INC DBA DAVIS SUPPLY  509 WESTLAND Dr  EDMOND, OK 73013  Property:  2200  NE 63rd  Oklahoma City, OK 73111  Legal Property Description attached as Exhibit   Property"
    company = extract_company_name(text)
    print (company)

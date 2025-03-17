import re

def clean_text(text):
    """Removes non-ASCII characters and extra spaces."""
    return re.sub(r'[^\x00-\x7F]+', ' ', text).strip()

def extract_address(text):
    try:
        if not text:
            return None, None, None, None
        
        text = clean_text(text)

        address_pattern = r'(\d+\s[\w\s.,#/-]+?(Way|St|Ave|Blvd|Rd|Dr|Lane|Ct|Pl|Terrace|Drive|Pkwy))\s*,?\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5}(-\d{4})?)?'

        match = re.search(address_pattern, text)
        if match:
            street = match.group(1)
            city = match.group(3)
            state = match.group(4)
            zip_code = match.group(5) if match.group(5) else None
            return street, city, state, zip_code

    except Exception:
        pass
    
    return None, None, None, None

# Test Case
address = extract_address("Sect 31-T14N-R3W Qtr SW SUMMERRIDGE PHASE II Block 008 Lot 033 also know as 16705 Valderama Way Edmond, OK 73012")
print(f"Address: {address}")

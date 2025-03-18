import re

def clean_text(text):
    """Removes non-ASCII characters and extra spaces."""
    return re.sub(r'[^\x00-\x7F]+', ' ', text).strip()

def extract_address(text):
    try:
        if not text:
            return None, None, None, None

        text = re.sub(r'(\bowned\s*by)([A-Z])', r'\1 \2', text)  
        text = clean_text(text)

        # Debug: Print cleaned text to verify
        print(f"Cleaned text: {text}")  # Debug print

        # Updated regex for more accurate street, city, state, zip extraction
        address_pattern = r'(\d+\s[\w\s#.,/-]+(?:Road|Rd|Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Court|Ct|Lane|Ln|Way|Pkwy)?)\s+([A-Za-z\s]+),\s*([A-Za-z]+(?:\s[A-Za-z]+)?)\s*(\d{5}(-\d{4})?)?'

        match = re.search(address_pattern, text)
        if match:
            street = match.group(1).strip()
            city = match.group(2).strip()
            state = match.group(3).strip()
            zip_code = match.group(4) if match.group(4) else None

            # Debug: Show matched results
            print(f"Match found: {street}, {city}, {state}, {zip_code}")

            return street, city, state, zip_code

    except Exception as e:
        print(f"Error in extract_address: {e}")

    return None, None, None, None

# Example test
address = extract_address("Deaundrey Green, Sr. Aylin Green 3208 S. Henney Rd. Choctaw, Oklahoma 73020 Subject Property: A")
print(f"Extracted Address: {address}")

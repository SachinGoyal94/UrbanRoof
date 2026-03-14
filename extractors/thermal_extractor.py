import pdfplumber
import re

def extract_thermal(pdf_path: str) -> list:
    """
    Extract per-page thermal readings from the thermal PDF.
    Each page = one thermal image + its temperature metadata.
    Returns a list of dicts, one per reading.
    """
    readings = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            reading = _parse_thermal_page(text, page_num + 1)
            if reading:
                readings.append(reading)

    return readings


def _parse_thermal_page(text: str, page_num: int) -> dict:
    """Parse hotspot, coldspot, emissivity, date from one thermal page."""
    reading = {"page": page_num}

    patterns = {
        "hotspot":     r"Hotspot\s*:\s*([\d.]+)\s*°?C",
        "coldspot":    r"Coldspot\s*:\s*([\d.]+)\s*°?C",
        "emissivity":  r"Emissivity\s*:\s*([\d.]+)",
        "reflected":   r"Reflected temperature\s*:\s*([\d.]+)\s*°?C",
        "date":        r"(\d{2}/\d{2}/\d{2,4})",
        "image_name":  r"Thermal image\s*:\s*(\S+\.JPG)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        reading[key] = match.group(1) if match else "Not Available"

    # Only return if we got at least hotspot/coldspot
    if reading["hotspot"] == "Not Available" and reading["coldspot"] == "Not Available":
        return None

    # Flag potential moisture: coldspot significantly below ambient (23°C baseline)
    try:
        coldspot_val = float(reading["coldspot"])
        reading["moisture_flag"] = coldspot_val < 22.0
    except ValueError:
        reading["moisture_flag"] = False

    return reading
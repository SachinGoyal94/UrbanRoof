"""
extractors/thermal_extractor.py

Extracts temperature readings and metadata from the thermal imaging PDF.
Each page in the thermal PDF typically contains:
  - One thermal image (IR camera capture)
  - One visual/reference photo
  - Temperature metadata: hotspot, coldspot, emissivity, date, device, image name

No area names are hardcoded here. Area matching is handled by the
Thermal Analyst Agent which cross-references readings with the orchestrator's
areas_identified list.

Works with any thermal PDF that follows the Bosch GTC / FLIR / similar format.
"""

import re
import pdfplumber


def extract_thermal(pdf_path: str) -> dict:
    """
    Extract all thermal readings from the thermal imaging PDF.

    Returns
    -------
    dict with keys:
        "readings"     : list of per-page thermal reading dicts
        "page_count"   : total pages in the thermal PDF
        "raw_text"     : full concatenated text (for agent use)
        "device_info"  : camera device details if found
    """
    readings   = []
    raw_text   = ""
    device_info = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                raw_text += f"\n--- PAGE {page_num} ---\n{page_text}"

                reading = _parse_thermal_page(page_text, page_num)
                if reading:
                    readings.append(reading)

                # Extract device info from first page
                if page_num == 1 and not device_info:
                    device_info = _parse_device_info(page_text)

    except Exception as e:
        print(f"  Warning: thermal extraction failed — {e}")
        return {
            "readings":    [],
            "page_count":  0,
            "raw_text":    "",
            "device_info": {},
            "error":       str(e),
        }

    # Flag moisture on all readings after we have ambient baseline
    ambient = _estimate_ambient(readings)
    for r in readings:
        r["ambient_baseline"] = ambient
        r["moisture_flag"]    = _check_moisture(r, ambient)
        r["temp_differential"] = _calc_differential(r)

    print(f"  Thermal: {len(readings)} readings extracted "
          f"from {page_count} pages  "
          f"(ambient baseline: {ambient}°C)")

    return {
        "readings":    readings,
        "page_count":  page_count,
        "raw_text":    raw_text.strip(),
        "device_info": device_info,
    }


# ---------------------------------------------------------------------------
# Per-page parser
# ---------------------------------------------------------------------------
def _parse_thermal_page(text: str, page_num: int) -> dict | None:
    """
    Parse one page of the thermal PDF.
    Returns None if no meaningful thermal data is found on the page.
    """
    reading = {"page": page_num}

    # ── Temperature values ──────────────────────────────────────
    patterns = {
        "hotspot_c":    [
            r"Hotspot\s*[:\-]?\s*([\d.]+)\s*°?C",
            r"Hot[- ]?spot\s*[:\-]?\s*([\d.]+)",
        ],
        "coldspot_c":   [
            r"Coldspot\s*[:\-]?\s*([\d.]+)\s*°?C",
            r"Cold[- ]?spot\s*[:\-]?\s*([\d.]+)",
        ],
        "emissivity":   [
            r"[Ee]missivity\s*[:\-]?\s*([\d.]+)",
            r"[Ee]\s*[:\-=]\s*([\d.]+)",
        ],
        "reflected_c":  [
            r"Reflected\s+[Tt]emp(?:erature)?\s*[:\-]?\s*([\d.]+)\s*°?C",
            r"[Rr]eflected\s*[:\-]?\s*([\d.]+)",
        ],
        "date":         [
            r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4})",
            r"(\d{4}[/\-\.]\d{2}[/\-\.]\d{2})",
        ],
        "image_name":   [
            r"(?:Thermal\s+image|Image)\s*[:\-]?\s*(\S+\.(?:JPG|jpg|PNG|png|IR))",
            r"(RB\d+X\.JPG)",
        ],
        "device":       [
            r"Device\s*[:\-]?\s*(.+?)(?:\s{2,}|$)",
            r"(GTC\s+\d+\s*\w+)",
            r"(FLIR\s+\w+)",
        ],
        "serial":       [
            r"Serial\s+[Nn]umber\s*[:\-]?\s*(\S+)",
        ],
    }

    for field, pattern_list in patterns.items():
        value = None
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                break
        reading[field] = value

    # ── Also grab any inline temperature readings (e.g. ~25.1°C markers) ──
    inline_temps = re.findall(r"~?([\d.]+)\s*°?C", text)
    reading["all_temp_mentions"] = [float(t) for t in inline_temps
                                     if _is_valid_temp(t)]

    # ── Discard pages with no temperature data ──────────────────
    if reading["hotspot_c"] is None and reading["coldspot_c"] is None:
        # Still keep if we found inline temps (might be a summary page)
        if not reading["all_temp_mentions"]:
            return None

    # ── Convert numeric fields to float ─────────────────────────
    for field in ["hotspot_c", "coldspot_c", "emissivity", "reflected_c"]:
        if reading[field] is not None:
            try:
                reading[field] = float(reading[field])
            except ValueError:
                reading[field] = None

    return reading


# ---------------------------------------------------------------------------
# Device info parser  (from first page)
# ---------------------------------------------------------------------------
def _parse_device_info(text: str) -> dict:
    info = {}
    device_match = re.search(
        r"Device\s*[:\-]?\s*(.+?)(?:\s{2,}|\n|$)",
        text, re.IGNORECASE
    )
    serial_match = re.search(
        r"Serial\s+[Nn]umber\s*[:\-]?\s*(\S+)",
        text, re.IGNORECASE
    )
    if device_match:
        info["device"] = device_match.group(1).strip()
    if serial_match:
        info["serial"] = serial_match.group(1).strip()
    return info


# ---------------------------------------------------------------------------
# Ambient baseline estimator
# ---------------------------------------------------------------------------
def _estimate_ambient(readings: list) -> float:
    """
    Estimate the ambient temperature from all readings.
    Uses the reflected temperature values if available,
    otherwise uses the median of all hotspot readings as a proxy.
    Falls back to 23°C (common indoor ambient used in the sample reports).
    """
    # Prefer reflected temperature (most accurate ambient indicator)
    reflected = [
        r["reflected_c"] for r in readings
        if r.get("reflected_c") is not None
    ]
    if reflected:
        return round(sum(reflected) / len(reflected), 1)

    # Fallback: median of hotspot values (rough proxy)
    hotspots = sorted(
        r["hotspot_c"] for r in readings
        if r.get("hotspot_c") is not None
    )
    if hotspots:
        mid = len(hotspots) // 2
        return round(hotspots[mid], 1)

    # Last resort default
    return 23.0


# ---------------------------------------------------------------------------
# Moisture detection
# ---------------------------------------------------------------------------
def _check_moisture(reading: dict, ambient: float) -> bool:
    """
    Flag moisture if the coldspot is significantly below ambient.
    Threshold: 3°C below ambient (industry standard for moisture detection
    via IR thermography in building inspections).

    Also flags if the temperature differential between hotspot and
    coldspot is unusually large (> 6°C), which can indicate active
    water migration even if absolute temps look normal.
    """
    coldspot = reading.get("coldspot_c")
    hotspot  = reading.get("hotspot_c")

    if coldspot is None:
        return False

    # Primary check: coldspot vs ambient
    if coldspot < (ambient - 3.0):
        return True

    # Secondary check: large differential
    if hotspot is not None and (hotspot - coldspot) > 6.0:
        return True

    return False


def _calc_differential(reading: dict) -> float | None:
    """Hotspot minus coldspot temperature differential."""
    h = reading.get("hotspot_c")
    c = reading.get("coldspot_c")
    if h is not None and c is not None:
        return round(h - c, 1)
    return None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _is_valid_temp(val: str) -> bool:
    """Filter out obviously wrong temperature values (e.g. year numbers)."""
    try:
        f = float(val)
        return 0.0 <= f <= 80.0   # reasonable indoor building temp range
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Convenience summary  (used by thermal_analyst agent for quick reference)
# ---------------------------------------------------------------------------
def build_area_thermal_map(readings: list, image_mapping: list) -> dict:
    """
    Group thermal readings by area using the orchestrator's image_mapping.

    Parameters
    ----------
    readings      : list from extract_thermal()["readings"]
    image_mapping : list from orchestrator output

    Returns
    -------
    dict: { area_name -> [list of matching readings] }
    """
    area_map = {}

    for entry in image_mapping:
        area      = entry.get("area_name", "")
        thm_pages = entry.get("thermal_pages", [])

        matched = [r for r in readings if r.get("page") in thm_pages]
        if matched:
            area_map[area] = matched

    return area_map


# ---------------------------------------------------------------------------
# Smoke test  (python thermal_extractor.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import json

    path = sys.argv[1] if len(sys.argv) > 1 else "Thermal_Images.pdf"

    print(f"Extracting thermal data from: {path}")
    result = extract_thermal(path)

    print(f"\nPages        : {result['page_count']}")
    print(f"Readings     : {len(result['readings'])}")
    print(f"Device       : {result.get('device_info', {})}")
    print(f"\nFirst 3 readings:")
    for r in result["readings"][:3]:
        print(json.dumps(r, indent=2))
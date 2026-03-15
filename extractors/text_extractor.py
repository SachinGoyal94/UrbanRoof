import pdfplumber

def extract_text(pdf_path: str) -> dict:
    """
    Extract structured text from the inspection PDF.
    Returns a dict with metadata, area observations, and summary table.
    """
    result = {
        "metadata": {},
        "areas": [],
        "summary_table": [],
        "raw_sections": {}
    }

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page_num, page in enumerate(pdf.pages, start=1):
            full_text += f"\n--- PAGE {page_num} ---\n"
            full_text += page.extract_text() or ""

        # Extract tables (summary table, checklists)
        all_tables = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if table:
                    all_tables.append(table)

        result["raw_text"]    = full_text
        result["all_tables"]  = all_tables
        result["page_count"]  = len(pdf.pages)

    # Parse key sections from raw text
    result["areas"]     = _parse_areas(full_text)
    result["metadata"]  = _parse_metadata(full_text)

    return result


def _parse_metadata(text: str) -> dict:
    """Pull property/client details from the top of the report."""
    metadata = {}
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "customer name" in line.lower():
            metadata["customer_name"] = lines[i + 1].strip() if i + 1 < len(lines) else "Not Available"
        if "date of inspection" in line.lower():
            metadata["inspection_date"] = line.split(":")[-1].strip()
        if "inspected by" in line.lower():
            metadata["inspector"] = line.split(":")[-1].strip()
        if "site address" in line.lower():
            metadata["address"] = lines[i + 1].strip() if i + 1 < len(lines) else "Not Available"
    return metadata


def _parse_areas(text: str) -> list:
    """
    Identify impacted area blocks from the inspection text.
    Looks for patterns like 'Impacted Area 1', 'BATHROOM', 'BALCONY' etc.
    """
    areas = []
    known_areas = [
        "hall", "bedroom", "master bedroom", "bathroom", "common bathroom",
        "balcony", "terrace", "external wall", "kitchen", "parking", "staircase"
    ]

    lines = text.lower().split("\n")
    current_area = None
    current_obs  = []

    for line in lines:
        matched = next((a for a in known_areas if a in line), None)
        if matched:
            if current_area:
                areas.append({
                    "area": current_area,
                    "observations": " ".join(current_obs).strip()
                })
            current_area = matched
            current_obs  = [line]
        elif current_area:
            current_obs.append(line)

    if current_area:
        areas.append({
            "area": current_area,
            "observations": " ".join(current_obs).strip()
        })

    return areas
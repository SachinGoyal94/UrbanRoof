from merger.conflict_handler import detect_conflicts

# Maps area names from text extraction to thermal page numbers
# Adjust this based on your actual documents
AREA_TO_THERMAL_PAGES = {
    "hall":              [1, 2],
    "bedroom":           [2, 3],
    "master bedroom":    [4, 5, 6],
    "common bathroom":   [3],
    "bathroom":          [4, 5],
    "balcony":           [6, 7],
    "terrace":           [8, 9],
    "external wall":     [10],
    "kitchen":           [7],
    "staircase":         [4],
    "parking":           [],
}

def merge_data(text_data: dict, thermal_readings: list, images: dict) -> dict:
    """
    Combine text observations + thermal readings into a
    structured context object ready to send to Gemini.
    """
    merged_areas = []

    for area_data in text_data.get("areas", []):
        area_name = area_data["area"]

        # Find matching thermal readings for this area
        page_nums   = AREA_TO_THERMAL_PAGES.get(area_name, [])
        matched_thermal = [
            t for t in thermal_readings
            if t.get("page") in page_nums
        ]

        # Summarise thermal findings
        thermal_summary = _summarise_thermal(matched_thermal)

        # Check for conflicts between visual and thermal
        conflicts = detect_conflicts(area_data["observations"], matched_thermal)

        merged_areas.append({
            "area":             area_name,
            "visual_obs":       area_data["observations"],
            "thermal":          thermal_summary,
            "conflicts":        conflicts,
            "has_moisture_flag": any(t.get("moisture_flag") for t in matched_thermal),
        })

    return {
        "metadata":   text_data.get("metadata", {}),
        "areas":      merged_areas,
        "images":     images,
        "structured": {
            "property_metadata": text_data.get("metadata", {}),
            "area_data":         merged_areas,
            "total_areas":       len(merged_areas),
        }
    }


def _summarise_thermal(readings: list) -> dict:
    if not readings:
        return {"available": False, "summary": "Not Available"}

    hotspots  = [float(r["hotspot"])  for r in readings if r.get("hotspot")  != "Not Available"]
    coldspots = [float(r["coldspot"]) for r in readings if r.get("coldspot") != "Not Available"]

    return {
        "available":   True,
        "max_hotspot": max(hotspots)  if hotspots  else "Not Available",
        "min_coldspot":min(coldspots) if coldspots else "Not Available",
        "reading_count": len(readings),
        "moisture_flagged": any(r.get("moisture_flag") for r in readings),
        "summary": (
            f"Hotspot {max(hotspots):.1f}°C, "
            f"Coldspot {min(coldspots):.1f}°C "
            f"across {len(readings)} reading(s)"
        ) if hotspots else "Not Available"
    }
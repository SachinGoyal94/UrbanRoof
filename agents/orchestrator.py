import json, config

PROMPT = """You are the lead building inspection coordinator.

You have been given three documents:
1. A visual inspection report (Sample Report) WITH PAGE MARKERS (--- PAGE N ---)
2. A thermal imaging report (Thermal Images) WITH PAGE MARKERS
3. A completed DDR sample (Main DDR) — use ONLY as a style/depth reference.
   Do NOT copy its content — it is a different property.

Read all three carefully and produce a master analysis plan.

CRITICAL INSTRUCTION FOR image_mapping: 
- Use the --- PAGE N --- markers in the text to identify which pages have images for each area.
- For each area identified, list the exact inspection_pages and thermal_pages where photos appear.
- Be thorough: scan the entire document for page markers and area names to build an accurate map.

Return JSON:
{
  "property_info": {
    "address": "string",
    "inspection_date": "string",
    "inspector": "string",
    "property_type": "string",
    "age_years": "string",
    "floors": "string",
    "previous_repairs": "string",
    "report_id": "string"
  },
  "areas_identified": [
    {
      "area_name": "string  (use the exact name as it appears in the document)",
      "has_visual_data": true/false,
      "has_thermal_data": true/false,
      "apparent_severity": "Critical|High|Medium|Low|Unknown",
      "key_issues_summary": "1-2 sentence summary"
    }
  ],
  "image_mapping": [
    {
      "area_name": "string  (must exactly match an area_name above)",
      "inspection_pages": [list of page numbers in inspection PDF with photos for this area],
      "thermal_pages":    [list of page numbers in thermal PDF for this area]
    }
  ],
  "document_quality_notes": "string"
}
"""
from google import genai
from google.genai import types

_client = genai.Client(api_key=config.GEMINI_API_KEY)

def run_orchestrator(insp_text: str, thermal_text: str,
                     sample_ddr_text: str, images: dict) -> dict:
    print("  [Orchestrator] Analyzing all documents...")

    # Build content parts — text only for orchestrator (planning pass)
    # NO CHARACTER LIMITS — preserve page markers for accurate image_mapping
    content = f"""
<sample_report>
{insp_text}
</sample_report>

<thermal_report>
{thermal_text}
</thermal_report>

<reference_ddr_style>
{sample_ddr_text[:4000]}
</reference_ddr_style>

{PROMPT}
"""
    response = _client.models.generate_content(
        model=config.MODEL_NAME,
        contents=content,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    result   = json.loads(response.text)
    print(f"  [Orchestrator] Found {len(result.get('areas_identified', []))} areas")
    return result
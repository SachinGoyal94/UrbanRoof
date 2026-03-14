import json, config


PROMPT = """You are the lead building inspection coordinator.
You have been given three documents:
1. A visual inspection report (Sample Report)
2. A thermal imaging report (Thermal Images)
3. A completed DDR sample (Main DDR) — use this ONLY to understand
   the expected depth, structure, and writing style of the final output.
   Do NOT copy content from it — it is a different property.

Your job: read all three carefully and produce a master analysis plan.

Return JSON with this structure:
{
  "property_info": {
    "address": "string",
    "inspection_date": "string",
    "inspector": "string",
    "property_type": "string",
    "age_years": "string",
    "floors": "string",
    "previous_repairs": "string"
  },
  "areas_identified": [
    {
      "area_name": "string",
      "has_visual_data": true/false,
      "has_thermal_data": true/false,
      "thermal_pages": [list of page numbers from thermal doc],
      "apparent_severity": "Critical|High|Medium|Low|Unknown",
      "key_issues_summary": "1-2 sentence summary of what is wrong here"
    }
  ],
  "document_quality_notes": "any observations about data gaps or conflicts",
  "expected_section_count": number
}
"""
from google import genai
from google.genai import types

_client = genai.Client(api_key=config.GEMINI_API_KEY)

def run_orchestrator(insp_text: str, thermal_text: str,
                     sample_ddr_text: str, images: dict) -> dict:
    print("  [Orchestrator] Analyzing all documents...")

    # Build content parts — text only for orchestrator (planning pass)
    content = f"""
<sample_report>
{insp_text[:8000]}
</sample_report>

<thermal_report>
{thermal_text[:4000]}
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

import json, config

PROMPT = """You are a structural and waterproofing root cause expert.

You receive combined visual inspection findings and thermal analysis per area.
Your job: determine the most probable root cause for each area's issues,
assess severity with clear reasoning, and identify any conflicts between
what the inspector saw and what the thermal data shows.

For severity:
- Critical: structural risk, immediate collapse/safety concern
- High: active leakage, moisture confirmed by thermal, will worsen quickly
- Medium: dampness present, not yet structural, needs attention within months
- Low: cosmetic, preventive action sufficient

Return JSON:
{
  "area_diagnoses": [
    {
      "area_name": "string",
      "root_cause": "Detailed explanation of why this problem exists",
      "contributing_factors": ["list of factors making it worse"],
      "severity": "Critical|High|Medium|Low",
      "severity_reasoning": "Explain exactly why this severity level was assigned",
      "visual_thermal_conflict": "Describe any conflict, or null if none",
      "if_delayed": "What will happen if this is not treated — specific consequences"
    }
  ],
  "overall_property_severity": "Critical|High|Medium|Low",
  "priority_areas": ["ordered list of area names, most urgent first"]
}
"""
from google import genai
from google.genai import types

_client = genai.Client(api_key=config.GEMINI_API_KEY)

def run_root_cause_analyst(inspection_analysis: dict,
                           thermal_analysis: dict) -> dict:
    print("  [Root Cause Analyst] Diagnosing causes and severity...")

    content = f"""
<inspection_findings>
{json.dumps(inspection_analysis, indent=2)}
</inspection_findings>

<thermal_findings>
{json.dumps(thermal_analysis, indent=2)}
</thermal_findings>

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
    print(f"  [Root Cause Analyst] Diagnosed {len(result.get('area_diagnoses', []))} areas")
    return result
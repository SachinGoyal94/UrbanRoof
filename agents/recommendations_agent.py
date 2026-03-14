import json, config


PROMPT = """You are a building repair and waterproofing specialist.

Based on the inspection findings, thermal analysis, and root cause diagnoses,
write specific, actionable repair recommendations for each area.

Use professional treatment terminology (grouting, PMM, Dr. Fixit URP, plaster
bonding coat, waterproof coating, RCC jacketing etc.) matching industry-standard
repair methods. Be specific about materials and steps.

Return JSON:
{
  "area_recommendations": [
    {
      "area_name": "string",
      "primary_treatment": "Name of the main treatment",
      "treatment_steps": [
        "Step 1: detailed instruction",
        "Step 2: ...",
        ...
      ],
      "materials_required": ["list of materials/products"],
      "priority": "Immediate|Short-term|Long-term",
      "estimated_scope": "Small patch|Area-wide|Full replacement",
      "precautions": "Any special precautions during treatment"
    }
  ],
  "general_recommendations": [
    "Any property-wide recommendations that apply across areas"
  ],
  "delayed_action_risks": [
    {
      "area_name": "string",
      "risk": "What happens if treatment is delayed"
    }
  ]
}
"""

from google import genai
from google.genai import types

_client = genai.Client(api_key=config.GEMINI_API_KEY)

def run_recommendations_agent(root_cause_analysis: dict,
                               inspection_analysis: dict) -> dict:
    print("  [Recommendations Agent] Writing repair treatments...")

    content = f"""
<root_cause_analysis>
{json.dumps(root_cause_analysis, indent=2)}
</root_cause_analysis>

<inspection_findings>
{json.dumps(inspection_analysis, indent=2)}
</inspection_findings>

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
    print(f"  [Recommendations Agent] Generated recommendations for "
          f"{len(result.get('area_recommendations', []))} areas")
    return result
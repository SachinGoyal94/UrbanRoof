import json, config


PROMPT_TEMPLATE = """You are a senior building inspection analyst.

You will receive the full text of a visual inspection report and a list
of areas to analyze. For each area, write a DETAILED observation section
matching the depth of a professional DDR report.

Be specific — mention exact locations (skirting level, ceiling, wall corner),
exact observations (dampness, efflorescence, spalling, hollowness, gaps in
tile joints), and the checklist inputs that were marked.

Areas to analyze: {areas}

Return JSON:
{{
  "area_analyses": [
    {{
      "area_name": "string",
      "negative_side": {{
        "leakage_at_walls": "Dampness|Seepage|Live Leakage|No Leakage|Not Available",
        "leakage_below_floor": "Dampness|Seepage|Live Leakage|No Leakage|Not Available",
        "leakage_season": "Monsoon|All Time|Not Sure|Not Available",
        "concealed_plumbing_issue": "Yes|No|Not Sure|Not Available",
        "detailed_observation": "Full paragraph describing exactly what was found"
      }},
      "positive_side": {{
        "gaps_in_tile_joints": "Yes|No|Not Sure|Not Available",
        "gaps_around_nahani_trap": "Yes|No|Not Sure|Not Available",
        "tiles_broken_or_loose": "Yes|No|Not Sure|Not Available",
        "detailed_observation": "Full paragraph describing the source/cause side"
      }},
      "image_labels": ["list of image captions that belong to this area from the report"]
    }}
  ]
}}
"""

from google import genai
from google.genai import types

_client = genai.Client(api_key=config.GEMINI_API_KEY)

def run_inspection_analyst(insp_text: str, areas: list) -> dict:
    print("  [Inspection Analyst] Extracting detailed observations...")
    area_names = [a["area_name"] for a in areas]

    prompt = f"""
<inspection_report>
{insp_text}
</inspection_report>

{PROMPT_TEMPLATE.format(areas=json.dumps(area_names))}
"""
    response = _client.models.generate_content(
        model=config.MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    result   = json.loads(response.text)
    print(f"  [Inspection Analyst] Analyzed {len(result.get('area_analyses', []))} areas")
    return result
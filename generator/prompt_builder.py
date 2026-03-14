import json

DDR_SYSTEM = """You are a senior building inspection analyst at UrbanRoof.
You receive pre-extracted structured data from two inspection documents:
  1. A visual inspection report (observations, checklists, area-by-area findings)
  2. A thermal imaging report (IR camera temperature readings per area)

Your task: generate a complete Detailed Diagnostic Report (DDR).

Strict rules:
- Never invent or assume facts not present in the provided data
- Write exactly "Not Available" for any missing field — never leave a field empty
- If visual and thermal data conflict for the same area, explicitly describe the conflict
- If moisture_flag is true for an area, classify severity as at least High
- Use plain, client-friendly language — avoid jargon
- Severity must be exactly one of: Critical / High / Medium / Low
- Priority must be exactly one of: Immediate / Short-term / Long-term
- Return ONLY a valid JSON object — no markdown, no prose outside JSON"""


DDR_SCHEMA = """
Return a JSON object with exactly these keys and structure:

{
  "property_summary": "2-3 sentence overview of overall property condition",

  "area_observations": [
    {
      "area": "area name",
      "visual_observation": "what the inspector saw",
      "thermal_reading": "thermal summary or Not Available",
      "combined_finding": "what both sources together indicate",
      "conflicts": ["list of conflicts or empty list"],
      "severity": "Critical|High|Medium|Low"
    }
  ],

  "root_causes": [
    {
      "area": "area name",
      "cause": "most probable root cause explanation"
    }
  ],

  "severity_assessment": [
    {
      "area": "area name",
      "level": "Critical|High|Medium|Low",
      "reasoning": "why this severity was assigned"
    }
  ],

  "recommended_actions": [
    {
      "area": "area name",
      "action": "specific repair or treatment recommended",
      "priority": "Immediate|Short-term|Long-term"
    }
  ],

  "additional_notes": "any observations that don't fit above sections",

  "missing_information": [
    "list each piece of data that was unavailable or unclear"
  ]
}
"""


def build_prompt(context: dict) -> str:
    structured = context["structured"]
    return f"""
{DDR_SYSTEM}

<inspection_data>
{json.dumps(structured, indent=2)}
</inspection_data>

{DDR_SCHEMA}
"""
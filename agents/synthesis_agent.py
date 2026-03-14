import json, config


PROMPT = """You are a senior DDR report writer at UrbanRoof.

You receive outputs from four specialist agents. Your job is to synthesize
everything into the final complete DDR content object. Write in clear,
professional, client-friendly language.

Every section must be fully written — no placeholders, no "see above",
no truncation. The property summary should be 3-4 sentences. Each area
observation should be a full paragraph. Severity reasoning should be
2-3 sentences minimum.

Return JSON with this exact structure:
{
  "property_summary": "3-4 sentence overview of the property condition",

  "area_observations": [
    {
      "area": "string",
      "negative_observation": "Full paragraph — what damage/symptoms were found",
      "positive_observation": "Full paragraph — what is causing it (source side)",
      "thermal_finding": "Full paragraph — what IR data shows, or Not Available",
      "combined_interpretation": "Full paragraph — what all data together means",
      "conflicts": ["any conflicts between visual and thermal, empty list if none"],
      "severity": "Critical|High|Medium|Low",
      "image_labels": ["image captions that belong here"]
    }
  ],

  "root_causes": [
    {
      "area": "string",
      "cause": "Detailed root cause paragraph",
      "contributing_factors": ["list"],
      "if_delayed": "Consequence paragraph"
    }
  ],

  "severity_assessment": [
    {
      "area": "string",
      "level": "Critical|High|Medium|Low",
      "reasoning": "Full reasoning paragraph"
    }
  ],

  "recommended_actions": [
    {
      "area": "string",
      "treatment_name": "string",
      "steps": ["step 1", "step 2", ...],
      "materials": ["material list"],
      "priority": "Immediate|Short-term|Long-term"
    }
  ],

  "additional_notes": "Any important notes not covered above",

  "missing_information": [
    "Each piece of data that was unavailable — be specific"
  ],

  "overall_severity": "Critical|High|Medium|Low",
  "priority_action_order": ["area names ordered most urgent to least"]
}
"""

from google import genai
from google.genai import types

_client = genai.Client(api_key=config.GEMINI_API_KEY)

def run_synthesis_agent(orchestrator_out: dict,
                        inspection_out:  dict,
                        thermal_out:     dict,
                        root_cause_out:  dict,
                        recommendations_out: dict) -> dict:
    print("  [Synthesis Agent] Merging all findings into final DDR content...")

    content = f"""
<orchestrator_plan>
{json.dumps(orchestrator_out, indent=2)}
</orchestrator_plan>

<inspection_analysis>
{json.dumps(inspection_out, indent=2)}
</inspection_analysis>

<thermal_analysis>
{json.dumps(thermal_out, indent=2)}
</thermal_analysis>

<root_cause_analysis>
{json.dumps(root_cause_out, indent=2)}
</root_cause_analysis>

<recommendations>
{json.dumps(recommendations_out, indent=2)}
</recommendations>

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
    print(f"  [Synthesis Agent] Built DDR with "
          f"{len(result.get('area_observations', []))} area sections")
    return result
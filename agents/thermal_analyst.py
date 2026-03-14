import json, config



PROMPT = """You are a thermal imaging specialist for building diagnostics.

Analyze the thermal report text below. For each thermal reading found:
- Extract hotspot and coldspot temperatures
- Identify which room/area the reading belongs to (match by page sequence
  and any area labels in the text)
- Flag moisture if coldspot is more than 3°C below the ambient (23°C baseline)
- Describe what the temperature differential indicates physically

Also cross-reference with the inspection areas list provided.

Return JSON:
{
  "thermal_readings": [
    {
      "page": number,
      "area_name": "best match area name",
      "hotspot_c": number or null,
      "coldspot_c": number or null,
      "emissivity": number or null,
      "date": "string",
      "moisture_flagged": true/false,
      "temperature_differential": number,
      "interpretation": "What this thermal reading indicates about the area condition",
      "severity_indication": "Critical|High|Medium|Low"
    }
  ],
  "area_thermal_summary": [
    {
      "area_name": "string",
      "reading_count": number,
      "worst_coldspot": number or null,
      "moisture_confirmed": true/false,
      "thermal_narrative": "Paragraph summarising all thermal findings for this area"
    }
  ]
}
"""
from google import genai
from google.genai import types

_client = genai.Client(api_key=config.GEMINI_API_KEY)

def run_thermal_analyst(thermal_text: str, areas: list) -> dict:
    print("  [Thermal Analyst] Interpreting IR readings...")
    area_names = [a["area_name"] for a in areas]

    content = f"""
<thermal_report>
{thermal_text}
</thermal_report>

<known_areas>
{json.dumps(area_names)}
</known_areas>

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
    print(f"  [Thermal Analyst] Processed {len(result.get('thermal_readings', []))} readings")
    return result
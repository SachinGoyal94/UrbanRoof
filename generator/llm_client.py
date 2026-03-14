from google import genai
from google.genai import types
import json
import config

# One client, reused across all calls
_client = genai.Client(api_key=config.GEMINI_API_KEY)

def generate_ddr(context: dict) -> dict:
    from generator.prompt_builder import build_prompt
    prompt = build_prompt(context)

    response = _client.models.generate_content(
        model=config.MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        cleaned = response.text.strip()
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
        return json.loads(cleaned)

def _parse_json_response(text: str) -> dict | None:
    if not text:
        return None

    # First attempt: parse as-is.
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    # Fallback: strip common markdown fence wrappers.
    cleaned = text.strip().removeprefix("```json").removeprefix("```")
    cleaned = cleaned.removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None

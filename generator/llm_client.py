import google.generativeai as genai
import json
import config
from generator.prompt_builder import build_prompt

genai.configure(api_key=config.GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name=config.MODEL_NAME,
    generation_config=genai.GenerationConfig(
        temperature=0.1,
        response_mime_type="application/json"  # forces clean JSON output
    )
)

def generate_ddr(context: dict) -> dict:
    prompt = build_prompt(context)

    print("  Sending to Gemini...")
    response = model.generate_content(prompt)

    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        # Fallback: strip any accidental markdown fences
        cleaned = response.text.strip()
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
        return json.loads(cleaned)
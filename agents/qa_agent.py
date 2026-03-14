import json, config


PROMPT = """You are a quality assurance reviewer for building inspection reports.

Review the synthesized DDR content against these criteria:
1. Every area identified in the plan has a corresponding observation section
2. No field contains placeholder text or is suspiciously short (< 20 words)
3. Severity levels are consistent — if thermal shows moisture, severity >= High
4. Every recommended action has at least 3 steps
5. Conflicts between visual/thermal are explicitly documented
6. Missing information section is honest and specific

Return JSON:
{
  "passed": true/false,
  "score": 0-100,
  "issues": [
    {
      "section": "which section has the issue",
      "area": "which area (if applicable)",
      "issue": "what is wrong",
      "fix": "what the synthesis agent should do to fix it"
    }
  ],
  "areas_missing": ["any areas from the plan that have no observation section"],
  "approved": true/false
}
"""
from google import genai
from google.genai import types

_client = genai.Client(api_key=config.GEMINI_API_KEY)

def run_qa_agent(synthesis_output: dict, orchestrator_plan: dict) -> dict:
    print("  [QA Agent] Validating DDR completeness...")

    content = f"""
<ddr_content>
{json.dumps(synthesis_output, indent=2)}
</ddr_content>

<original_plan>
{json.dumps(orchestrator_plan, indent=2)}
</original_plan>

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
    score    = result.get("score", 0)
    passed   = result.get("passed", False)
    print(f"  [QA Agent] Score: {score}/100 — {'PASSED' if passed else 'ISSUES FOUND'}")
    return result
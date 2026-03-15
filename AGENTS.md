# AGENTS Guide for UrbanRoof

## Project intent and entrypoints
- This service generates a **DDR PDF** from two uploaded PDFs (visual inspection + thermal report).
- API entrypoint: `main.py` (`POST /generate`, `GET /health`) using FastAPI.
- Orchestration entrypoint: `pipeline.py::run_pipeline(job_id, insp_path, thermal_path)`.

## End-to-end data flow (follow this before editing)
- `extractors/text_extractor.py::extract_text` pulls raw text/tables and derives `metadata` + `areas`.
- `extractors/thermal_extractor.py::extract_thermal` parses per-page temperatures and sets `moisture_flag`.
- `extractors/image_extractor.py::extract_images` rasterizes selected inspection pages + all thermal pages to `temp_images/<job_id>/`.
- `merger/data_merger.py::merge_data` aligns area observations to thermal pages via `AREA_TO_THERMAL_PAGES` and computes summaries/conflicts.
- `generator/llm_client.py::generate_ddr` sends merged `context["structured"]` to Gemini using `generator/prompt_builder.py` rules/schema.
- `report/pdf_assembler.py::assemble_pdf` renders final report with ReportLab into `outputs/<job_id>.pdf`.

## Codebase-specific conventions and assumptions
- Missing values are standardized as the exact string `"Not Available"` (extractors, prompt rules, PDF rendering).
- Area matching is heuristic and string-based (`_parse_areas` known list + `AREA_TO_THERMAL_PAGES` lookup); update both when adding area names.
- Thermal conflict logic is keyword-driven (`"no leakage"`, `"dampness"`, `"seepage"`) in `merger/conflict_handler.py`.
- Image extraction is intentionally tied to sample report layout via `INSPECTION_IMAGE_PAGES`; changing source PDF layout requires remapping.
- `generator/llm_client.py` enforces JSON output and strips markdown fences as fallback.

## Practical workflows
- Install deps from `requirements.txt`; service startup is typically:
  - `python -m uvicorn main:app --reload`
- Required env var: `GEMINI_KEY` (loaded in `config.py` via `python-dotenv`).
- Runtime directories expected/written: `uploads/`, `outputs/`, `temp_images/` (auto-created where configured).
- Fast smoke test pattern:
  - `GET /health` returns `{\"status\": \"ok\"}`.
  - `POST /generate` with multipart fields `inspection_pdf` and `thermal_pdf` returns a generated PDF file.

## Integration notes and gotchas
- External dependencies: Gemini API (`google-generativeai`) and Poppler-backed PDF rasterization (`pdf2image`).
- `report/pdf_assembler.py` reads `ddr.get("property_metadata", {})`, but prompt schema returns `property_summary` + lists; metadata may show `Not Available` unless explicitly included upstream.
- `merger/thermal_extractor.py` exists but is empty/stale; active thermal parser is `extractors/thermal_extractor.py`.
- `pipeline.py` uses print-based progress logs with job-id prefix (useful for tracing one request).

## When adding features
- Keep pipeline stage boundaries intact (extract -> merge -> LLM -> PDF) unless redesigning all contracts.
- If you add fields to LLM JSON schema, update both prompt schema (`generator/prompt_builder.py`) and PDF consumer (`report/pdf_assembler.py`).
- Prefer extending existing dict contracts rather than replacing keys expected by downstream stages.


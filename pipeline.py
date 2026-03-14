from extractors.text_extractor    import extract_text
from extractors.image_extractor   import extract_images
from extractors.thermal_extractor import extract_thermal
from merger.data_merger           import merge_data
from generator.llm_client         import generate_ddr
from report.pdf_assembler         import assemble_pdf
import config, os

os.makedirs(config.OUTPUT_DIR, exist_ok=True)

def run_pipeline(job_id: str, insp_path: str, thermal_path: str) -> str:
    print(f"\n[{job_id[:8]}] Starting pipeline...")

    print(f"[{job_id[:8]}] Step 1 — Extracting text...")
    text_data = extract_text(insp_path)

    print(f"[{job_id[:8]}] Step 2 — Extracting thermal readings...")
    thermal = extract_thermal(thermal_path)
    print(f"  Found {len(thermal)} thermal readings")

    print(f"[{job_id[:8]}] Step 3 — Extracting images...")
    images = extract_images(insp_path, thermal_path, job_id)
    print(f"  Extracted {len(images)} images")

    print(f"[{job_id[:8]}] Step 4 — Merging data...")
    context = merge_data(text_data, thermal, images)

    print(f"[{job_id[:8]}] Step 5 — Generating DDR via Gemini...")
    ddr_json = generate_ddr(context)

    print(f"[{job_id[:8]}] Step 6 — Assembling PDF...")
    output_path = os.path.join(config.OUTPUT_DIR, f"{job_id}.pdf")
    assemble_pdf(ddr_json, images, output_path)

    return output_path
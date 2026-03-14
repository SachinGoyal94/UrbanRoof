import json, os, config
import pdfplumber
from extractors.image_extractor import extract_images

from agents.orchestrator         import run_orchestrator
from agents.inspection_analyst   import run_inspection_analyst
from agents.thermal_analyst      import run_thermal_analyst
from agents.root_cause_analyst   import run_root_cause_analyst
from agents.recommendations_agent import run_recommendations_agent
from agents.synthesis_agent      import run_synthesis_agent
from agents.qa_agent             import run_qa_agent
from report.pdf_assembler        import assemble_pdf

os.makedirs(config.OUTPUT_DIR, exist_ok=True)


def _read_pdf_text(path: str) -> str:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def run_pipeline(job_id: str, insp_path: str,
                 thermal_path: str, sample_ddr_path: str) -> str:
    print(f"\n{'='*50}")
    print(f"Job {job_id[:8]} — Starting multi-agent pipeline")
    print(f"{'='*50}")

    # ── Read all documents ─────────────────────────────────
    print("\n[1/7] Reading documents...")
    insp_text       = _read_pdf_text(insp_path)
    thermal_text    = _read_pdf_text(thermal_path)
    sample_ddr_text = _read_pdf_text(sample_ddr_path)

    # ── Extract images ─────────────────────────────────────
    print("\n[2/7] Extracting images...")
    images = extract_images(insp_path, thermal_path, job_id)
    print(f"  Extracted {len(images)} images")

    # ── Agent 1: Orchestrator ──────────────────────────────
    print("\n[3/7] Running Orchestrator Agent...")
    orchestrator_out = run_orchestrator(
        insp_text, thermal_text, sample_ddr_text, images
    )
    areas = orchestrator_out.get("areas_identified", [])

    # ── Agents 2-5: Specialists (sequential for stability) ─
    print("\n[4/7] Running Specialist Agents...")
    inspection_out     = run_inspection_analyst(insp_text, areas)
    thermal_out        = run_thermal_analyst(thermal_text, areas)
    root_cause_out     = run_root_cause_analyst(inspection_out, thermal_out)
    recommendations_out = run_recommendations_agent(root_cause_out, inspection_out)

    # ── Agent 6: Synthesis ─────────────────────────────────
    print("\n[5/7] Running Synthesis Agent...")
    synthesis_out = run_synthesis_agent(
        orchestrator_out, inspection_out, thermal_out,
        root_cause_out, recommendations_out
    )

    # ── Agent 7: QA — retry once if issues found ───────────
    print("\n[6/7] Running QA Agent...")
    qa_result = run_qa_agent(synthesis_out, orchestrator_out)

    if not qa_result.get("approved") and qa_result.get("issues"):
        print("  QA found issues — running synthesis retry...")
        synthesis_out = run_synthesis_agent(
            orchestrator_out, inspection_out, thermal_out,
            root_cause_out, recommendations_out
            # In a full implementation you'd pass qa_result["issues"]
            # back into the synthesis prompt here
        )

    # ── PDF Assembly ───────────────────────────────────────
    print("\n[7/7] Assembling PDF...")
    output_path = os.path.join(config.OUTPUT_DIR, f"{job_id}.pdf")

    # Attach property info from orchestrator to synthesis output
    synthesis_out["property_info"] = orchestrator_out.get("property_info", {})

    assemble_pdf(synthesis_out, images, output_path)

    print(f"\n{'='*50}")
    print(f"Done — {output_path}")
    print(f"QA Score: {qa_result.get('score', 'N/A')}/100")
    print(f"{'='*50}\n")

    return output_path
"""
pipeline.py

Multi-agent DDR generation pipeline.
Orchestrates all 7 agents in sequence and assembles the final PDF.

Call:
    output_path = run_pipeline(job_id, insp_path, thermal_path, sample_ddr_path)
"""

import os
import json
import pdfplumber

import config
from extractors.image_extractor       import extract_images
from agents.orchestrator              import run_orchestrator
from agents.inspection_analyst        import run_inspection_analyst
from agents.thermal_analyst           import run_thermal_analyst
from agents.root_cause_analyst        import run_root_cause_analyst
from agents.recommendations_agent     import run_recommendations_agent
from agents.synthesis_agent           import run_synthesis_agent
from agents.qa_agent                  import run_qa_agent
from report.pdf_assembler             import assemble_pdf

os.makedirs(config.OUTPUT_DIR,   exist_ok=True)
os.makedirs(config.UPLOAD_DIR,   exist_ok=True)
os.makedirs(config.TEMP_IMG_DIR, exist_ok=True)


def _read_pdf_text(path: str) -> str:
    """Extract all text from a PDF, page by page."""
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"  Warning: could not read text from {path} — {e}")
    return text


def _log(job_id: str, step: int, total: int, msg: str):
    short = job_id[:8]
    print(f"[{short}] ({step}/{total}) {msg}")


def run_pipeline(
    job_id:          str,
    insp_path:       str,
    thermal_path:    str,
    sample_ddr_path: str,
) -> str:
    """
    Run the full multi-agent DDR pipeline.

    Parameters
    ----------
    job_id           : unique job identifier
    insp_path        : local path to the inspection report PDF
    thermal_path     : local path to the thermal images PDF
    sample_ddr_path  : local path to the sample DDR PDF (style reference)

    Returns
    -------
    output_path : local path of the generated DDR PDF
    """
    TOTAL_STEPS = 9
    sep = "=" * 55

    print(f"\n{sep}")
    print(f"  DDR Pipeline  |  Job {job_id[:8]}")
    print(f"{sep}")

    _log(job_id, 1, TOTAL_STEPS, "Reading document texts …")

    insp_text       = _read_pdf_text(insp_path)
    thermal_text    = _read_pdf_text(thermal_path)
    sample_ddr_text = _read_pdf_text(sample_ddr_path)

    print(f"    Inspection  : {len(insp_text):,} chars")
    print(f"    Thermal     : {len(thermal_text):,} chars")
    print(f"    Sample DDR  : {len(sample_ddr_text):,} chars")

    if not insp_text.strip():
        raise ValueError(
            "Inspection PDF produced no text — "
            "check the file is not scanned/image-only."
        )

    # ── Step 2: Extract all images (no hardcoding) ───────────────
    _log(job_id, 2, TOTAL_STEPS, "Extracting images from both PDFs …")

    images = extract_images(insp_path, thermal_path, job_id)

    print(f"    Total images : {len(images)}")
    print(f"    Inspection   : "
          f"{sum(1 for k in images if k.startswith('inspection'))}")
    print(f"    Thermal      : "
          f"{sum(1 for k in images if k.startswith('thermal'))}")

    # ── Step 3: Orchestrator — understand all docs + build image map ──
    _log(job_id, 3, TOTAL_STEPS,
         "Orchestrator Agent — analysing documents …")

    orchestrator_out = run_orchestrator(
        insp_text       = insp_text,
        thermal_text    = thermal_text,
        sample_ddr_text = sample_ddr_text,
        images          = images,
    )

    areas         = orchestrator_out.get("areas_identified", [])
    image_mapping = orchestrator_out.get("image_mapping", [])

    print(f"    Areas found       : {len(areas)}")
    print(f"    Image map entries : {len(image_mapping)}")

    if not areas:
        raise ValueError(
            "Orchestrator returned no areas. "
            "The inspection PDF may not contain readable observations."
        )

    # Log the area → page mapping so it's easy to debug
    if image_mapping:
        print("    Image mapping:")
        for entry in image_mapping:
            insp_pgs = entry.get("inspection_pages", [])
            thm_pgs  = entry.get("thermal_pages", [])
            print(f"      '{entry.get('area_name', '')}' "
                  f"→ inspection {insp_pgs}, thermal {thm_pgs}")

    # ── Step 4: Inspection Analyst ───────────────────────────────
    _log(job_id, 4, TOTAL_STEPS,
         "Inspection Analyst Agent — extracting observations …")

    inspection_out = run_inspection_analyst(
        insp_text = insp_text,
        areas     = areas,
    )

    print(f"    Areas analysed : "
          f"{len(inspection_out.get('area_analyses', []))}")

    # ── Step 5: Thermal Analyst ──────────────────────────────────
    _log(job_id, 5, TOTAL_STEPS,
         "Thermal Analyst Agent — interpreting IR readings …")

    thermal_out = run_thermal_analyst(
        thermal_text = thermal_text,
        areas        = areas,
    )

    print(f"    Thermal readings  : "
          f"{len(thermal_out.get('thermal_readings', []))}")
    print(f"    Area summaries    : "
          f"{len(thermal_out.get('area_thermal_summary', []))}")

    # ── Step 6: Root Cause Analyst ───────────────────────────────
    _log(job_id, 6, TOTAL_STEPS,
         "Root Cause Analyst Agent — diagnosing causes …")

    root_cause_out = run_root_cause_analyst(
        inspection_analysis = inspection_out,
        thermal_analysis    = thermal_out,
    )

    print(f"    Diagnoses produced : "
          f"{len(root_cause_out.get('area_diagnoses', []))}")
    print(f"    Overall severity   : "
          f"{root_cause_out.get('overall_property_severity', 'Unknown')}")

    # ── Step 7: Recommendations Agent ───────────────────────────
    _log(job_id, 7, TOTAL_STEPS,
         "Recommendations Agent — writing repair treatments …")

    recommendations_out = run_recommendations_agent(
        root_cause_analysis = root_cause_out,
        inspection_analysis = inspection_out,
    )

    print(f"    Recommendations : "
          f"{len(recommendations_out.get('area_recommendations', []))}")

    # ── Step 8: Synthesis Agent ──────────────────────────────────
    _log(job_id, 8, TOTAL_STEPS,
         "Synthesis Agent — merging all findings into DDR content …")

    synthesis_out = run_synthesis_agent(
        orchestrator_out    = orchestrator_out,
        inspection_out      = inspection_out,
        thermal_out         = thermal_out,
        root_cause_out      = root_cause_out,
        recommendations_out = recommendations_out,
    )

    print(f"    DDR sections built : "
          f"{len(synthesis_out.get('area_observations', []))} areas")

    # ── QA pass — retry synthesis once if issues found ───────────
    qa_result = run_qa_agent(
        synthesis_output  = synthesis_out,
        orchestrator_plan = orchestrator_out,
    )

    qa_score  = qa_result.get("score", 0)
    qa_passed = qa_result.get("approved", False)
    print(f"    QA score : {qa_score}/100  "
          f"({'PASSED' if qa_passed else 'ISSUES — retrying synthesis'})")

    if not qa_passed:
        issues = qa_result.get("issues", [])
        if issues:
            print(f"    Issues   : {len(issues)}")
            for iss in issues[:3]:   # print first 3 for visibility
                print(f"      • [{iss.get('section','')}] "
                      f"{iss.get('issue','')}")

            # Re-run synthesis with QA feedback injected
            synthesis_out = _synthesis_retry(
                orchestrator_out    = orchestrator_out,
                inspection_out      = inspection_out,
                thermal_out         = thermal_out,
                root_cause_out      = root_cause_out,
                recommendations_out = recommendations_out,
                qa_issues           = issues,
            )
            print(f"    Retry complete — "
                  f"{len(synthesis_out.get('area_observations', []))} areas")

    # Attach property info so assembler can read it
    synthesis_out["property_info"] = orchestrator_out.get("property_info", {})

    # ── Step 9: Assemble PDF ─────────────────────────────────────
    _log(job_id, 9, TOTAL_STEPS, "Assembling final PDF …")

    output_path = os.path.join(config.OUTPUT_DIR, f"{job_id}.pdf")

    assemble_pdf(
        ddr           = synthesis_out,
        images        = images,
        image_mapping = image_mapping,   # ← Gemini-built page map
        output_path   = output_path,
    )

    print(f"\n{sep}")
    print(f"  DONE  |  Job {job_id[:8]}")
    print(f"  Output : {output_path}")
    print(f"  QA     : {qa_score}/100")
    print(f"{sep}\n")

    return output_path


# ---------------------------------------------------------------------------
# Synthesis retry with QA feedback
# ---------------------------------------------------------------------------
def _synthesis_retry(
    orchestrator_out:    dict,
    inspection_out:      dict,
    thermal_out:         dict,
    root_cause_out:      dict,
    recommendations_out: dict,
    qa_issues:           list,
) -> dict:
    """
    Re-run the synthesis agent with QA issues fed back in as
    explicit instructions to fix.
    """
    from agents.synthesis_agent import run_synthesis_agent_with_feedback

    # Build a plain-English list of fixes
    fix_instructions = "\n".join(
        f"- [{iss.get('section', '')} / {iss.get('area', '')}] "
        f"{iss.get('issue', '')} → Fix: {iss.get('fix', '')}"
        for iss in qa_issues
    )

    return run_synthesis_agent_with_feedback(
        orchestrator_out    = orchestrator_out,
        inspection_out      = inspection_out,
        thermal_out         = thermal_out,
        root_cause_out      = root_cause_out,
        recommendations_out = recommendations_out,
        fix_instructions    = fix_instructions,
    )
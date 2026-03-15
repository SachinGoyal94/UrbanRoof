import os
from pdf2image import convert_from_path
import config

os.makedirs(config.TEMP_IMG_DIR, exist_ok=True)


def extract_images(insp_path: str, thermal_path: str, job_id: str) -> dict:
    """
    Extract ALL pages from both PDFs as images.
    No hardcoded area names or page numbers.
    Returns a flat dict:
        "inspection_page_1"  -> "/path/to/file.jpg"
        "inspection_page_2"  -> ...
        "thermal_page_1"     -> ...
    The mapping from page → area is handled by the orchestrator agent.
    """
    job_dir = os.path.join(config.TEMP_IMG_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    images = {}
    images.update(_extract_all_pages(insp_path,    job_dir, prefix="inspection", dpi=130))
    images.update(_extract_all_pages(thermal_path, job_dir, prefix="thermal",    dpi=100))

    print(f"  Extracted {len(images)} images total "
          f"({sum(1 for k in images if k.startswith('inspection'))} inspection, "
          f"{sum(1 for k in images if k.startswith('thermal'))} thermal)")
    return images


def _extract_all_pages(pdf_path: str, job_dir: str,
                        prefix: str, dpi: int) -> dict:
    result = {}
    try:
        pages = convert_from_path(pdf_path, dpi=dpi)
        for i, page in enumerate(pages, start=1):
            out = os.path.join(job_dir, f"{prefix}_page_{i}.jpg")
            page.save(out, "JPEG", quality=85)
            result[f"{prefix}_page_{i}"] = out
    except Exception as e:
        print(f"  Warning: could not extract {prefix} images — {e}")
    return result
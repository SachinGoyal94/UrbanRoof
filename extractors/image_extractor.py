import os
from pdf2image import convert_from_path
from PIL import Image
import config

os.makedirs(config.TEMP_IMG_DIR, exist_ok=True)

# Pages in the inspection PDF that contain relevant photos
# (based on the sample: pages 27-36 are thermal refs + visual refs)
INSPECTION_IMAGE_PAGES = {
    "hall_ceiling":           27,
    "bedroom_skirting":       28,
    "passage_skirting":       29,
    "staircase_master_bed":   30,
    "master_bed_skirting":    31,
    "master_bed2_skirting":   32,
    "master_bed_bathroom":    33,
    "external_wall":          34,
    "common_bathroom":        34,
    "balcony":                35,
    "external_wall_master":   35,
    "terrace_master_bed2":    36,
}

def extract_images(insp_path: str, thermal_path: str, job_id: str) -> dict:
    """
    Extract key images from both PDFs.
    Returns a dict mapping area names to local image file paths.
    """
    images = {}
    job_dir = os.path.join(config.TEMP_IMG_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Extract inspection report images (pages with thermal+visual pairs)
    images.update(_extract_inspection_images(insp_path, job_dir))

    # Extract thermal images (all pages — each is one thermal reading)
    images.update(_extract_thermal_images(thermal_path, job_dir))

    return images


def _extract_inspection_images(pdf_path: str, job_dir: str) -> dict:
    result = {}
    pages_needed = list(set(INSPECTION_IMAGE_PAGES.values()))

    try:
        pages = convert_from_path(
            pdf_path,
            dpi=120,
            first_page=min(pages_needed),
            last_page=max(pages_needed)
        )

        page_offset = min(pages_needed) - 1
        for label, page_num in INSPECTION_IMAGE_PAGES.items():
            idx = page_num - 1 - page_offset
            if 0 <= idx < len(pages):
                out_path = os.path.join(job_dir, f"insp_{label}.jpg")
                pages[idx].save(out_path, "JPEG", quality=85)
                result[label] = out_path
    except Exception as e:
        print(f"  Warning: inspection image extraction failed — {e}")

    return result


def _extract_thermal_images(pdf_path: str, job_dir: str) -> dict:
    result = {}
    try:
        pages = convert_from_path(pdf_path, dpi=100)
        for i, page in enumerate(pages):
            out_path = os.path.join(job_dir, f"thermal_page_{i+1}.jpg")
            page.save(out_path, "JPEG", quality=80)
            result[f"thermal_{i+1}"] = out_path
    except Exception as e:
        print(f"  Warning: thermal image extraction failed — {e}")

    return result
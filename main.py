from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import shutil, uuid, os
from pipeline import run_pipeline
import config

app = FastAPI(title="DDR Report Generator", version="1.0")

os.makedirs(config.UPLOAD_DIR, exist_ok=True)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

@app.post("/generate", summary="Upload 2 PDFs, get DDR report back")
async def generate_report(
    inspection_pdf: UploadFile = File(..., description="Visual inspection report PDF"),
    thermal_pdf:    UploadFile = File(..., description="Thermal imaging report PDF"),
):
    job_id = str(uuid.uuid4())
    insp_path    = f"{config.UPLOAD_DIR}/{job_id}_inspection.pdf"
    thermal_path = f"{config.UPLOAD_DIR}/{job_id}_thermal.pdf"

    try:
        with open(insp_path, "wb")    as f: shutil.copyfileobj(inspection_pdf.file, f)
        with open(thermal_path, "wb") as f: shutil.copyfileobj(thermal_pdf.file, f)

        output_path = run_pipeline(job_id, insp_path, thermal_path)

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=f"DDR_{job_id[:8]}.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up uploads
        for p in [insp_path, thermal_path]:
            if os.path.exists(p): os.remove(p)

@app.get("/health")
def health(): return {"status": "ok"}
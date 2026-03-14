"""
main.py  —  DDR Report Generator API
Run with:  uvicorn main:app --reload --port 8000
Test UI:   http://localhost:8000/docs
"""

import os
import shutil
import uuid
import traceback
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import config
from pipeline import run_pipeline

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DDR Report Generator",
    description=(
        "Upload an inspection report PDF, a thermal images PDF, and a sample "
        "DDR PDF. The multi-agent system reads all three and produces a "
        "professional Detailed Diagnostic Report."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (swap for Redis/SQLite for production)
JOBS: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Ensure directories exist on startup
# ---------------------------------------------------------------------------
for d in [config.UPLOAD_DIR, config.OUTPUT_DIR, config.TEMP_IMG_DIR]:
    os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _save_upload(upload: UploadFile, dest: str):
    with open(dest, "wb") as f:
        shutil.copyfileobj(upload.file, f)


def _cleanup(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


def _run_job(job_id: str, insp_path: str,
             thermal_path: str, sample_ddr_path: str):
    """Background task that runs the full pipeline and updates job status."""
    JOBS[job_id]["status"]     = "processing"
    JOBS[job_id]["started_at"] = datetime.now().isoformat()

    try:
        output_path = run_pipeline(
            job_id, insp_path, thermal_path, sample_ddr_path
        )
        JOBS[job_id]["status"]       = "done"
        JOBS[job_id]["output_path"]  = output_path
        JOBS[job_id]["completed_at"] = datetime.now().isoformat()
        print(f"[{job_id[:8]}] Job complete → {output_path}")

    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"]  = str(e)
        JOBS[job_id]["trace"]  = traceback.format_exc()
        print(f"[{job_id[:8]}] Job FAILED: {e}")

    finally:
        # clean up uploaded source files
        _cleanup(insp_path, thermal_path, sample_ddr_path)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {
        "service": "DDR Report Generator",
        "version": "2.0.0",
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "jobs_in_memory": len(JOBS)}


# ── Synchronous endpoint (simpler, waits for result) ────────────────────────
@app.post(
    "/generate",
    tags=["Report"],
    summary="Generate DDR report (synchronous — waits for result)",
    response_description="Returns the generated PDF file directly.",
)
async def generate_sync(
    inspection_pdf: UploadFile = File(
        ..., description="Visual inspection report PDF"
    ),
    thermal_pdf: UploadFile = File(
        ..., description="Thermal imaging report PDF"
    ),
    sample_ddr_pdf: UploadFile = File(
        ..., description="Sample DDR PDF used as format/depth reference"
    ),
):
    """
    Upload all three PDFs and receive the generated DDR report back
    as a downloadable PDF.

    This is a **synchronous** call — it blocks until the report is ready
    (typically 30–90 seconds depending on the number of areas).
    Use `/generate/async` + `/status/{job_id}` for non-blocking operation.
    """
    job_id       = str(uuid.uuid4())
    insp_path    = f"{config.UPLOAD_DIR}/{job_id}_inspection.pdf"
    thermal_path = f"{config.UPLOAD_DIR}/{job_id}_thermal.pdf"
    sample_path  = f"{config.UPLOAD_DIR}/{job_id}_sample_ddr.pdf"

    _save_upload(inspection_pdf, insp_path)
    _save_upload(thermal_pdf,    thermal_path)
    _save_upload(sample_ddr_pdf, sample_path)

    try:
        output_path = run_pipeline(
            job_id, insp_path, thermal_path, sample_path
        )
    except Exception as e:
        _cleanup(insp_path, thermal_path, sample_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _cleanup(insp_path, thermal_path, sample_path)

    if not os.path.exists(output_path):
        raise HTTPException(
            status_code=500,
            detail="Pipeline completed but output PDF was not found."
        )

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"DDR_Report_{job_id[:8]}.pdf",
        headers={"X-Job-ID": job_id},
    )


# ── Async endpoint (returns job_id immediately) ──────────────────────────────
@app.post(
    "/generate/async",
    tags=["Report"],
    summary="Generate DDR report (async — returns job_id immediately)",
    status_code=202,
)
async def generate_async(
    background_tasks: BackgroundTasks,
    inspection_pdf: UploadFile = File(
        ..., description="Visual inspection report PDF"
    ),
    thermal_pdf: UploadFile = File(
        ..., description="Thermal imaging report PDF"
    ),
    sample_ddr_pdf: UploadFile = File(
        ..., description="Sample DDR PDF used as format/depth reference"
    ),
):
    """
    Upload all three PDFs. Returns a **job_id** immediately.
    Poll `GET /status/{job_id}` until `status == done`, then
    download the report from `GET /download/{job_id}`.
    """
    job_id       = str(uuid.uuid4())
    insp_path    = f"{config.UPLOAD_DIR}/{job_id}_inspection.pdf"
    thermal_path = f"{config.UPLOAD_DIR}/{job_id}_thermal.pdf"
    sample_path  = f"{config.UPLOAD_DIR}/{job_id}_sample_ddr.pdf"

    _save_upload(inspection_pdf, insp_path)
    _save_upload(thermal_pdf,    thermal_path)
    _save_upload(sample_ddr_pdf, sample_path)

    JOBS[job_id] = {
        "job_id":      job_id,
        "status":      "queued",
        "created_at":  datetime.now().isoformat(),
        "started_at":  None,
        "completed_at":None,
        "output_path": None,
        "error":       None,
    }

    background_tasks.add_task(
        _run_job, job_id, insp_path, thermal_path, sample_path
    )

    return {
        "job_id":      job_id,
        "status":      "queued",
        "status_url":  f"/status/{job_id}",
        "download_url":f"/download/{job_id}",
        "message":     "Job queued. Poll /status/{job_id} for progress.",
    }


@app.get(
    "/status/{job_id}",
    tags=["Report"],
    summary="Poll job status",
)
def job_status(job_id: str):
    """
    Returns the current status of an async job.

    Possible statuses:
    - `queued`     — waiting to start
    - `processing` — pipeline is running
    - `done`       — complete, download at `/download/{job_id}`
    - `failed`     — something went wrong, see `error` field
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    job  = JOBS[job_id]
    resp = {
        "job_id":      job_id,
        "status":      job["status"],
        "created_at":  job.get("created_at"),
        "started_at":  job.get("started_at"),
        "completed_at":job.get("completed_at"),
    }
    if job["status"] == "done":
        resp["download_url"] = f"/download/{job_id}"
    if job["status"] == "failed":
        resp["error"] = job.get("error", "Unknown error")

    return resp


@app.get(
    "/download/{job_id}",
    tags=["Report"],
    summary="Download the generated DDR PDF",
)
def download_report(job_id: str):
    """
    Download the completed DDR PDF for a finished async job.
    Returns 404 if the job doesn't exist.
    Returns 409 if the job hasn't finished yet.
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    job = JOBS[job_id]

    if job["status"] == "queued" or job["status"] == "processing":
        raise HTTPException(
            status_code=409,
            detail=f"Job is still {job['status']}. Try again later."
        )
    if job["status"] == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Job failed: {job.get('error', 'Unknown error')}"
        )

    output_path = job.get("output_path")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(
            status_code=404,
            detail="Output file not found on server."
        )

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"DDR_Report_{job_id[:8]}.pdf",
    )


@app.get(
    "/jobs",
    tags=["Report"],
    summary="List all jobs (dev/debug use)",
)
def list_jobs():
    return {
        "total": len(JOBS),
        "jobs": [
            {
                "job_id":     jid,
                "status":     j["status"],
                "created_at": j.get("created_at"),
            }
            for jid, j in JOBS.items()
        ],
    }


@app.delete(
    "/jobs/{job_id}",
    tags=["Report"],
    summary="Delete a job and its output file",
)
def delete_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    output_path = JOBS[job_id].get("output_path")
    _cleanup(output_path)
    del JOBS[job_id]
    return {"deleted": job_id}
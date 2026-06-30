from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.ingestion.pipeline import process_document
from backend.ingestion.pipeline_async import process_document_async
from backend.ingestion.jobs import get_job_sync, get_all_jobs_sync
from backend.logging_config import logger

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class ProcessRequest(BaseModel):
    document_id: str


@router.post("/process")
async def process(request: ProcessRequest):
    try:
        result = process_document(request.document_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/process-async")
async def process_async(request: ProcessRequest):
    try:
        job_id = await process_document_async(request.document_id)
        return {"job_id": job_id, "status": "started", "document_id": request.document_id}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Async processing failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/job/{job_id}")
def job_status(job_id: str):
    job = get_job_sync(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/jobs")
def all_jobs():
    return get_all_jobs_sync()

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.ingestion.pipeline import process_document
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

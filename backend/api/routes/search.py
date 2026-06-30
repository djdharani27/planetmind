from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from backend.search.hybrid_search import hybrid_search
from backend.logging_config import logger

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    equipment: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    document_type: str | None = None
    technician: str | None = None
    failure_type: str | None = None


@router.post("")
async def search(request: SearchRequest):
    try:
        search_query = request.query
        filters = []
        if request.equipment:
            filters.append(f"equipment:{request.equipment}")
        if request.failure_type:
            filters.append(f"failure:{request.failure_type}")
        if request.document_type:
            filters.append(f"type:{request.document_type}")
        if request.technician:
            filters.append(f"technician:{request.technician}")
        if request.date_from:
            filters.append(f"date_from:{request.date_from}")
        if request.date_to:
            filters.append(f"date_to:{request.date_to}")
        if filters:
            search_query = f"{search_query} {' '.join(filters)}"

        results = hybrid_search(search_query, request.top_k)
        results["applied_filters"] = {
            k: getattr(request, k) for k in ["equipment", "date_from", "date_to", "document_type", "technician", "failure_type"]
            if getattr(request, k)
        }
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(500, str(e))

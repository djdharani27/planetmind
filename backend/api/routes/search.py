from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.search.hybrid_search import hybrid_search
from backend.logging_config import logger

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


@router.post("")
async def search(request: SearchRequest):
    try:
        results = hybrid_search(request.query, request.top_k)
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(500, str(e))

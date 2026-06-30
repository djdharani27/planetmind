from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.llm.lessons_engine import analyze_lessons
from backend.logging_config import logger

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


class LessonsRequest(BaseModel):
    query: str
    equipment_type: str | None = None
    top_k: int = 15


@router.post("/analyze")
async def lessons_analysis(request: LessonsRequest):
    try:
        result = analyze_lessons(request.query, request.top_k)
        return result
    except Exception as e:
        logger.error(f"Lessons analysis failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/warnings")
async def proactive_warnings(request: LessonsRequest):
    query = f"Generate proactive safety and failure warnings for {request.equipment_type or 'all equipment'}. Check recent incidents, near-misses, and known failure patterns. {request.query}"
    try:
        result = analyze_lessons(query, request.top_k)
        return result
    except Exception as e:
        logger.error(f"Proactive warnings failed: {e}")
        raise HTTPException(500, str(e))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.llm.maintenance_rca import analyze_maintenance
from backend.logging_config import logger

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


class MaintenanceRequest(BaseModel):
    query: str
    equipment_id: str | None = None
    time_range_days: int = 90
    top_k: int = 15


@router.post("/rca")
async def root_cause_analysis(request: MaintenanceRequest):
    try:
        result = analyze_maintenance(request.query, request.top_k)
        return result
    except Exception as e:
        logger.error(f"RCA failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/predict")
async def predictive_maintenance(request: MaintenanceRequest):
    query = f"Predict maintenance needs for {request.equipment_id or 'all equipment'} in next {request.time_range_days} days. Consider failure history, recent inspections, and operating conditions."
    try:
        result = analyze_maintenance(query, request.top_k)
        return result
    except Exception as e:
        logger.error(f"Predictive maintenance failed: {e}")
        raise HTTPException(500, str(e))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.llm.compliance_intel import analyze_compliance
from backend.logging_config import logger

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


class ComplianceRequest(BaseModel):
    query: str
    regulation: str | None = None
    top_k: int = 15


@router.post("/analyze")
async def compliance_analysis(request: ComplianceRequest):
    try:
        result = analyze_compliance(request.query, request.top_k)
        return result
    except Exception as e:
        logger.error(f"Compliance analysis failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/audit")
async def generate_audit_package(request: ComplianceRequest):
    query = f"Generate audit evidence package for {request.regulation or 'all applicable regulations'}. Include inspection records, procedures, and compliance status. {request.query}"
    try:
        result = analyze_compliance(query, request.top_k)
        return result
    except Exception as e:
        logger.error(f"Audit package generation failed: {e}")
        raise HTTPException(500, str(e))

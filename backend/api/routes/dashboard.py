from fastapi import APIRouter
from backend.database.database import get_connection

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]
    by_status = conn.execute(
        "SELECT processing_status, COUNT(*) as c FROM documents GROUP BY processing_status"
    ).fetchall()
    conn.close()

    return {
        "total_documents": total,
        "by_status": {r["processing_status"]: r["c"] for r in by_status},
    }

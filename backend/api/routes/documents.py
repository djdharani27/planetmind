from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from backend.api import document_service as svc
from backend.models.document import (
    DocumentResponse,
    UploadResponse,
    DocumentListResponse,
)
from backend.ingestion.pipeline import process_document as full_pipeline
from backend.logging_config import logger
import threading

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _process_in_thread(doc_id: str):
    """Run full processing pipeline (OCR, chunking, embeddings, entities, graph) in background thread."""
    try:
        logger.info(f"Background full pipeline started for {doc_id}")
        result = full_pipeline(doc_id)
        steps = result.get("steps", {})
        logger.info(
            f"Full pipeline complete for {doc_id}: "
            f"ocr={steps.get('ocr','?')}, parse={steps.get('parse','?')}, "
            f"embed={steps.get('embed','?')}, entities={steps.get('entities','?')}, "
            f"graph={steps.get('graph','?')}"
        )
    except Exception as e:
        logger.error(f"Background full pipeline failed for {doc_id}: {e}")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    try:
        content = await file.read()
        doc = svc.save_upload(content, file.filename, file.content_type)
        threading.Thread(target=_process_in_thread, args=(doc["id"],), daemon=True).start()
        return {
            "status": "success",
            "document": DocumentResponse(**doc),
            "message": f"Uploaded {file.filename} — processing in background",
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("", response_model=DocumentListResponse)
async def list_documents(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    docs = svc.list_documents()
    total = len(docs)
    start = (page - 1) * limit
    paged = docs[start:start + limit]
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "documents": [DocumentResponse(**d) for d in paged],
    }


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    doc = svc.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return DocumentResponse(**doc)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    ok = svc.delete_document(doc_id)
    if not ok:
        raise HTTPException(404, "Document not found")
    return {"status": "deleted", "id": doc_id}

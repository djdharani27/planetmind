from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.api import document_service as svc
from backend.models.document import (
    DocumentResponse,
    UploadResponse,
    DocumentListResponse,
)
from backend.logging_config import logger
import subprocess
import sys
import threading
from pathlib import Path

router = APIRouter(prefix="/api/documents", tags=["documents"])

_script_path = Path(__file__).resolve().parent.parent.parent.parent / "process_docs.py"


def _process_in_thread(doc_id: str):
    try:
        logger.info(f"Background processing started for {doc_id}")
        result = subprocess.run(
            [sys.executable, str(_script_path), doc_id],
            capture_output=True, text=True, timeout=120,
            cwd=str(_script_path.parent),
        )
        logger.info(f"Processing output for {doc_id}: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"Processing stderr for {doc_id}: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.error(f"Processing timed out for {doc_id}")
    except Exception as e:
        logger.error(f"Background processing failed for {doc_id}: {e}")


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
async def list_documents():
    docs = svc.list_documents()
    return {"total": len(docs), "documents": [DocumentResponse(**d) for d in docs]}


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

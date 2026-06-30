from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.api import document_service as svc
from backend.models.document import (
    DocumentResponse,
    UploadResponse,
    DocumentListResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    try:
        content = await file.read()
        doc = svc.save_upload(content, file.filename, file.content_type)
        return {
            "status": "success",
            "document": DocumentResponse(**doc),
            "message": f"Uploaded {file.filename}",
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

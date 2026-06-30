from pydantic import BaseModel
from typing import Optional
from datetime import datetime


ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "image/jpeg": "jpg",
    "image/png": "png",
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_timestamp: str
    processing_status: str
    storage_path: str
    metadata: dict = {}


class UploadResponse(BaseModel):
    status: str
    document: DocumentResponse
    message: str


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentResponse]


class ErrorResponse(BaseModel):
    status: str
    message: str


def validate_file_type(content_type: str) -> Optional[str]:
    return ALLOWED_TYPES.get(content_type)


def validate_file_size(size: int) -> bool:
    return 0 < size <= MAX_FILE_SIZE

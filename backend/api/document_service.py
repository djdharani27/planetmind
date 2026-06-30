import uuid
import shutil
import json
from pathlib import Path
from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.models.document import validate_file_type, validate_file_size
from backend.logging_config import logger


def _parse_row(row: dict) -> dict:
    d = dict(row)
    if isinstance(d.get("metadata"), str):
        try:
            d["metadata"] = json.loads(d["metadata"])
        except json.JSONDecodeError:
            d["metadata"] = {}
    return d


def save_upload(file_content: bytes, filename: str, file_type: str) -> dict:
    ext = validate_file_type(file_type)
    if not ext:
        raise ValueError(f"Unsupported file type: {file_type}")

    if not validate_file_size(len(file_content)):
        raise ValueError(f"File too large: {len(file_content)} bytes")

    doc_id = str(uuid.uuid4())
    storage_dir = settings.uploads_dir / doc_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / filename

    with open(file_path, "wb") as f:
        f.write(file_content)

    conn = get_connection()
    conn.execute(
        """INSERT INTO documents (id, filename, file_type, file_size, storage_path, upload_timestamp, processing_status, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            doc_id,
            filename,
            file_type,
            len(file_content),
            str(file_path),
            datetime.now(timezone.utc).isoformat(),
            "uploaded",
            "{}",
        ),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()

    logger.info(f"Document uploaded: {filename} ({doc_id})")
    return _parse_row(row)


def list_documents() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM documents ORDER BY upload_timestamp DESC").fetchall()
    conn.close()
    return [_parse_row(r) for r in rows]


def get_document(doc_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return _parse_row(row) if row else None


def update_status(doc_id: str, status: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE documents SET processing_status = ? WHERE id = ?", (status, doc_id))
    conn.commit()
    conn.close()


def delete_document(doc_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    storage_dir = settings.uploads_dir / doc_id
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
    logger.info(f"Document deleted: {doc_id}")
    return True

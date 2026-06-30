import asyncio
import uuid
from pathlib import Path
from backend.config import settings
from backend.database.database import get_connection
from backend.ingestion.ocr_detector import detect_document_type, extract_native_text
from backend.ingestion.paddleocr.ocr_pipeline import run_ocr
from backend.ingestion.docling.parser import parse_document
from backend.ingestion.chunking.chunker import chunk_document
from backend.embeddings.embedder import generate_and_store_embeddings
from backend.llm.entity_extractor import extract_entities
from backend.graph.graph_builder import build_knowledge_graph
from backend.ingestion.text_extractors import extract_text_by_type
from backend.ingestion.jobs import start_job, update_progress, complete_job, fail_job
from backend.logging_config import logger


async def process_document_async(doc_id: str, llm_client=None) -> str:
    job_id = f"process_{doc_id}_{uuid.uuid4().hex[:8]}"
    await start_job(job_id, "document_processing")

    asyncio.create_task(_run_pipeline(job_id, doc_id, llm_client))
    return job_id


async def _run_pipeline(job_id: str, doc_id: str, llm_client=None):
    try:
        conn = get_connection()
        doc = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        conn.close()

        if not doc:
            await fail_job(job_id, "Document not found")
            return

        doc = dict(doc)
        file_path = Path(doc["storage_path"])
        file_type = doc["file_type"]

        _update_status_sync(doc_id, "processing")
        await update_progress(job_id, "upload", "complete", 5)

        # OCR detection
        detection = detect_document_type(file_path, file_type)
        await update_progress(job_id, "ocr_detect", "complete", 10)

        if detection["needs_ocr"]:
            await update_progress(job_id, "ocr", "running", 15)
            ocr_data = run_ocr(doc_id, file_path)
            text = ocr_data["total_text"]
            await update_progress(job_id, "ocr", "complete", 25)
        else:
            try:
                text = extract_native_text(file_path)
            except Exception:
                text = detection.get("text_sample", "")
            if not text:
                text = extract_text_by_type(file_path, file_type)
            await update_progress(job_id, "ocr", "native", 20)

        text = (text or "").strip()
        if not text:
            _update_status_sync(doc_id, "failed")
            await fail_job(job_id, "No text extracted")
            return

        # Parse
        await update_progress(job_id, "parse", "running", 30)
        try:
            parsed = parse_document(doc_id, text)
            await update_progress(job_id, "parse", "complete", 40)
        except Exception as e:
            logger.error(f"Parse failed: {e}")
            parsed = {"sections": []}
            await update_progress(job_id, "parse", "failed", 40)

        # Chunk
        await update_progress(job_id, "chunk", "running", 50)
        try:
            chunks = chunk_document(doc_id, parsed, text)
            await update_progress(job_id, "chunk", "complete", 60)
        except Exception as e:
            logger.error(f"Chunk failed: {e}")
            chunks = []
            await update_progress(job_id, "chunk", "failed", 60)

        # Embeddings
        if chunks:
            await update_progress(job_id, "embed", "running", 70)
            try:
                generate_and_store_embeddings(doc_id, chunks)
                await update_progress(job_id, "embed", "complete", 75)
            except Exception as e:
                logger.warning(f"Embed failed: {e}")
                await update_progress(job_id, "embed", "skipped", 75)

        # Entities
        await update_progress(job_id, "entities", "running", 80)
        try:
            entities = extract_entities(doc_id, text, llm_client)
            await update_progress(job_id, "entities", "complete", 90)
        except Exception as e:
            logger.error(f"Entities failed: {e}")
            entities = []
            await update_progress(job_id, "entities", "failed", 90)

        # Graph
        if entities:
            await update_progress(job_id, "graph", "running", 92)
            try:
                build_knowledge_graph(doc_id, entities)
                await update_progress(job_id, "graph", "complete", 100)
            except Exception as e:
                logger.warning(f"Graph failed: {e}")
                await update_progress(job_id, "graph", "skipped", 100)

        _update_status_sync(doc_id, "ready")
        await complete_job(job_id, {"document_id": doc_id, "status": "ready"})
        logger.info(f"Async processing complete for {doc_id} (job {job_id})")

    except Exception as e:
        logger.error(f"Pipeline job {job_id} failed: {e}")
        _update_status_sync(doc_id, "failed")
        await fail_job(job_id, str(e))


def _update_status_sync(doc_id: str, status: str):
    conn = get_connection()
    conn.execute("UPDATE documents SET processing_status = ? WHERE id = ?", (status, doc_id))
    conn.commit()
    conn.close()

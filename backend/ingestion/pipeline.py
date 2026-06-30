import json
from pathlib import Path
from datetime import datetime, timezone
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
from backend.logging_config import logger


def process_document(doc_id: str, llm_client=None) -> dict:
    """Run the full processing pipeline on a document."""
    conn = get_connection()
    doc = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()

    if not doc:
        raise ValueError(f"Document not found: {doc_id}")

    doc = dict(doc)
    file_path = Path(doc["storage_path"])
    file_type = doc["file_type"]

    # Step 1: Check status and update
    if doc["processing_status"] != "uploaded":
        logger.info(f"Resuming processing for {doc_id} from status: {doc['processing_status']}")

    _update_status(doc_id, "processing")
    steps = {"ocr": "skipped", "parse": "skipped", "chunk": "skipped", "embed": "skipped", "entities": "skipped", "graph": "skipped"}

    # Step 2: OCR detection
    detection = detect_document_type(file_path, file_type)

    if detection["needs_ocr"]:
        logger.info(f"Running OCR on {doc_id}")
        ocr_data = run_ocr(doc_id, file_path)
        text = ocr_data["total_text"]
        steps["ocr"] = "completed"
    else:
        logger.info(f"Native text extraction for {doc_id}")
        try:
            text = extract_native_text(file_path)
        except Exception:
            text = detection.get("text_sample", "")
        if not text:
            try:
                text = extract_text_by_type(file_path, file_type)
            except Exception:
                text = ""
        steps["ocr"] = "native_extraction"

    text = (text or "").strip()
    if not text:
        _update_status(doc_id, "failed")
        return {"status": "failed", "error": "No text extracted", "steps": steps}

    # Step 4: Parse
    try:
        parsed = parse_document(doc_id, text)
        steps["parse"] = "completed"
    except Exception as e:
        logger.error(f"Parsing failed for {doc_id}: {e}")
        steps["parse"] = "failed"

    # Step 5: Chunk
    try:
        chunks = chunk_document(doc_id, parsed if steps["parse"] == "completed" else {"sections": []}, text)
        steps["chunk"] = "completed"
    except Exception as e:
        logger.error(f"Chunking failed for {doc_id}: {e}")
        chunks = []
        steps["chunk"] = "failed"

    # Step 6: Embeddings
    if chunks:
        try:
            generate_and_store_embeddings(doc_id, chunks)
            steps["embed"] = "completed"
        except Exception as e:
            logger.warning(f"Embedding failed for {doc_id}: {e}, continuing")
            steps["embed"] = "failed"

    # Step 7: Entity extraction
    try:
        entities = extract_entities(doc_id, text, llm_client)
        steps["entities"] = "completed"
    except Exception as e:
        logger.error(f"Entity extraction failed for {doc_id}: {e}")
        entities = []
        steps["entities"] = "failed"

    # Step 8: Knowledge graph
    if entities:
        try:
            build_knowledge_graph(doc_id, entities)
            steps["graph"] = "completed"
        except Exception as e:
            logger.warning(f"Graph construction failed for {doc_id}: {e}, continuing")
            steps["graph"] = "failed"

    _update_status(doc_id, "ready")
    logger.info(f"Processing complete for {doc_id}: {steps}")
    return {"status": "ready", "steps": steps}


def _update_status(doc_id: str, status: str):
    conn = get_connection()
    conn.execute("UPDATE documents SET processing_status = ? WHERE id = ?", (status, doc_id))
    conn.commit()
    conn.close()

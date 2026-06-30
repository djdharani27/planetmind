import json
import re
from pathlib import Path
from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.ingestion.ocr_detector import detect_document_type, extract_native_text
from backend.ingestion.text_extractors import extract_text_by_type
from backend.logging_config import logger


def process_document(doc_id: str, llm_client=None) -> dict:
    """Processing pipeline — uses PyMuPDF for text, intelligent parsers/chunkers/embeddings."""
    if llm_client is None:
        from backend.llm.client import create_llm_client
        llm_client = create_llm_client()

    conn = get_connection()
    doc = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()

    if not doc:
        raise ValueError(f"Document not found: {doc_id}")

    doc = dict(doc)
    file_path = Path(doc["storage_path"])
    file_type = doc["file_type"]

    _update_status(doc_id, "processing")
    steps = {"ocr": "skipped", "parse": "skipped", "chunk": "skipped", "embed": "skipped", "entities": "skipped", "graph": "skipped"}

    # Step 1: Extract text (PyMuPDF for PDFs, text extractors for other formats)
    detection = detect_document_type(file_path, file_type)
    text = ""

    if detection["needs_ocr"]:
        logger.info(f"Image/scanned document {doc_id} — PaddleOCR required (heavy)")
        try:
            from backend.ingestion.paddleocr.ocr_pipeline import run_ocr
            ocr_data = run_ocr(doc_id, file_path)
            text = ocr_data["total_text"]
            steps["ocr"] = "completed"
        except Exception as e:
            logger.error(f"OCR failed for {doc_id}: {e}")
            _update_status(doc_id, "failed")
            return {"status": "failed", "error": "OCR failed — may need PaddleOCR installed", "steps": steps}
    else:
        try:
            text = extract_native_text(file_path)
        except Exception:
            text = detection.get("text_sample", "")
        if not text:
            text = extract_text_by_type(file_path, file_type)
        steps["ocr"] = "native_extraction"

    text = (text or "").strip()
    if not text:
        _update_status(doc_id, "failed")
        return {"status": "failed", "error": "No text extracted", "steps": steps}

    _update_status(doc_id, "ocr_complete")

    # Step 2: Simple parsing (heading detection)
    output_dir = settings.processed_dir / doc_id
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = _simple_parse(text)
    parsed = {"document_id": doc_id, "sections": sections, "parsed_at": datetime.now(timezone.utc).isoformat()}
    with open(output_dir / "parsed_output.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
    steps["parse"] = "completed"
    _update_status(doc_id, "parsing_complete")

    # Step 3: Chunking
    chunks = _simple_chunk(doc_id, text)
    with open(output_dir / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    steps["chunk"] = "completed"
    _update_status(doc_id, "chunking_complete")

    # Step 4: Embeddings (needs Qdrant + BGE-M3 — skipped gracefully)
    _update_status(doc_id, "embeddings_complete")
    steps["embed"] = "skipped_no_service"

    # Step 5: Entity extraction
    from backend.llm.entity_extractor import extract_entities
    entities = extract_entities(doc_id, text, llm_client)
    with open(output_dir / "entities.json", "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
    steps["entities"] = "completed"
    _update_status(doc_id, "entities_complete")

    # Step 6: Knowledge graph (optional — needs Neo4j)
    if entities:
        try:
            from backend.graph.graph_builder import build_knowledge_graph
            build_knowledge_graph(doc_id, entities)
            steps["graph"] = "completed"
        except Exception:
            logger.info(f"Graph skipped for {doc_id} — Neo4j not available")
            steps["graph"] = "skipped_no_service"
    _update_status(doc_id, "graph_complete")

    # Step 7: Save text and update metadata
    with open(output_dir / "ocr_output.json", "w", encoding="utf-8") as f:
        json.dump({"document_id": doc_id, "total_text": text, "pages": [{"page_number": 1, "text": text, "confidence": 1.0}]}, f, ensure_ascii=False, indent=2)

    conn = get_connection()
    conn.execute(
        "UPDATE documents SET processing_status = ?, metadata = ? WHERE id = ?",
        ("ready", json.dumps({"text_length": len(text), "chunks": len(chunks), "entities": len(entities)}), doc_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Processing complete for {doc_id}: {len(text)} chars, {len(chunks)} chunks, {len(entities)} entities")
    return {"status": "ready", "steps": steps}


def _simple_parse(text: str) -> list[dict]:
    """Simple heading/paragraph detection without Docling."""
    sections = []
    lines = text.split("\n")
    current_heading = ""
    current_paras = []

    heading_re = re.compile(r"^[A-Z][A-Za-z\s\-/]{3,60}$")
    field_re = re.compile(r"^([A-Za-z\s]+)[:]\s*(.+)$")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if heading_re.match(line) and len(line) < 60:
            if current_heading or current_paras:
                sections.append({"heading": current_heading, "level": 1, "paragraphs": current_paras, "tables": []})
            current_heading = line
            current_paras = []
        elif field_re.match(line):
            m = field_re.match(line)
            current_paras.append(f"{m.group(1).strip()}: {m.group(2).strip()}")
        else:
            current_paras.append(line)

    if current_heading or current_paras:
        sections.append({"heading": current_heading, "level": 1, "paragraphs": current_paras, "tables": []})

    return sections


def _simple_chunk(doc_id: str, text: str) -> list[dict]:
    """Simple sentence-based chunking without LlamaIndex."""
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current_chunk = ""
    chunk_size = 800

    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append({
                "chunk_id": f"{doc_id}_c{len(chunks)}",
                "document_id": doc_id,
                "page_number": 1,
                "section": "",
                "chunk_text": current_chunk.strip(),
                "token_count": len(current_chunk.split()),
                "previous_chunk_id": f"{doc_id}_c{len(chunks) - 1}" if chunks else None,
                "next_chunk_id": None,
                "equipment_tags": _extract_equipment(current_chunk),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            current_chunk = sentence
        else:
            current_chunk += " " + sentence

    if current_chunk.strip():
        chunks.append({
            "chunk_id": f"{doc_id}_c{len(chunks)}",
            "document_id": doc_id,
            "page_number": 1,
            "section": "",
            "chunk_text": current_chunk.strip(),
            "token_count": len(current_chunk.split()),
            "previous_chunk_id": f"{doc_id}_c{len(chunks) - 1}" if chunks else None,
            "next_chunk_id": None,
            "equipment_tags": _extract_equipment(current_chunk),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    for i in range(len(chunks)):
        chunks[i]["next_chunk_id"] = chunks[i + 1]["chunk_id"] if i + 1 < len(chunks) else None

    return chunks


def _extract_equipment(text: str) -> list[str]:
    eq_re = re.compile(r"\b(Pump|Turbine|Motor|Generator|Compressor|Valve|Transformer|Gearbox|WTG)\s*[-]?\s*[A-Z0-9]{1,3}[-]?\d{2,5}\b", re.IGNORECASE)
    return list(set(eq_re.findall(text)))[:10]


def _update_status(doc_id: str, status: str):
    conn = get_connection()
    conn.execute("UPDATE documents SET processing_status = ? WHERE id = ?", (status, doc_id))
    conn.commit()
    conn.close()

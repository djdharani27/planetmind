import json
import re
from pathlib import Path
from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


def chunk_document(doc_id: str, parsed: dict, text: str) -> list[dict]:
    """Chunk document using LlamaIndex Node Parser by headings, sections, and token limits."""
    from llama_index.core.node_parser import (
        SentenceSplitter,
        SemanticSplitterNodeParser,
    )
    from llama_index.core.schema import Document

    chunk_size = 512
    chunk_overlap = 64

    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separator="\n\n",
    )

    documents = [Document(text=text, metadata={"doc_id": doc_id})]
    nodes = splitter.get_nodes_from_documents(documents)

    chunks = []
    for idx, node in enumerate(nodes):
        chunk = {
            "chunk_id": f"{doc_id}_c{idx}",
            "document_id": doc_id,
            "page_number": node.metadata.get("page", 1),
            "section": node.metadata.get("section", ""),
            "chunk_text": node.get_content(),
            "token_count": node.metadata.get("tokens", 0),
            "previous_chunk_id": f"{doc_id}_c{idx - 1}" if idx > 0 else None,
            "next_chunk_id": f"{doc_id}_c{idx + 1}" if idx < len(nodes) - 1 else None,
            "equipment_tags": _extract_equipment_tags(text),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        chunks.append(chunk)

    output_dir = settings.processed_dir / doc_id
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = output_dir / "chunks.json"

    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    conn = get_connection()
    conn.execute(
        "UPDATE documents SET processing_status = ? WHERE id = ?",
        ("chunking_complete", doc_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Chunking complete for {doc_id}: {len(chunks)} chunks")
    return chunks


def _extract_equipment_tags(text: str) -> list[str]:
    equipment_re = re.compile(r"\b(Pump|Turbine|Motor|Generator|Compressor|Valve|Transformer|Gearbox)\s+[A-Z]{1,3}[-]\d{2,5}\b", re.IGNORECASE)
    return list(set(equipment_re.findall(text)))[:10]


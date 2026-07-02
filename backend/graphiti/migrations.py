"""One-shot migration from legacy entities.json files to Graphiti Episodes.

Scans all storage/processed/*/entities.json files and creates Graphiti Episodes
for each document. Idempotent — checks for existing episodes before creating.
"""

import json
from pathlib import Path
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


async def migrate_legacy_entities() -> dict:
    """Migrate all legacy entity JSON files to Graphiti Episodes.

    Reads entities.json from each processed document directory and ingests
    the corresponding document text as a Graphiti Episode.

    Returns:
        dict with migrated_count, skipped_count, failed_count, total_entities.
    """
    from backend.graphiti.service import get_graphiti

    svc = get_graphiti()
    if not svc.is_available:
        await svc.initialize()
    if not svc.is_available:
        return {"error": "Graphiti not available", "migrated_count": 0, "skipped_count": 0, "failed_count": 0}

    proc_dir: Path = settings.processed_dir
    if not proc_dir.exists():
        return {"error": "No processed directory", "migrated_count": 0, "skipped_count": 0, "failed_count": 0}

    conn = get_connection()
    docs = {}
    try:
        rows = conn.execute("SELECT id, filename FROM documents").fetchall()
        for r in rows:
            docs[r["id"]] = r["filename"]
    finally:
        conn.close()

    migrated = 0
    skipped = 0
    failed = 0
    total_entities = 0

    for child in sorted(proc_dir.iterdir()):
        if not child.is_dir():
            continue

        entities_file = child / "entities.json"
        ocr_file = child / "ocr_output.json"
        doc_id = child.name

        if not entities_file.exists():
            skipped += 1
            continue

        filename = docs.get(doc_id, doc_id[:8])

        try:
            entities_data = json.loads(entities_file.read_text(encoding="utf-8"))
            entity_count = len(entities_data) if isinstance(entities_data, list) else 0
            total_entities += entity_count
        except Exception:
            entity_count = 0

        text = ""
        if ocr_file.exists():
            try:
                ocr_data = json.loads(ocr_file.read_text(encoding="utf-8"))
                text = ocr_data.get("total_text", "")
            except Exception:
                pass

        if not text:
            skipped += 1
            continue

        try:
            result = await svc.ingest_document_episode(
                doc_id=doc_id,
                filename=filename,
                text=text,
            )
            if "error" in result:
                failed += 1
                logger.warning(f"Migration failed for {doc_id}: {result['error']}")
            else:
                migrated += 1
                logger.info(f"Migrated {doc_id} — {filename} ({entity_count} legacy entities)")
        except Exception as e:
            failed += 1
            logger.error(f"Migration error for {doc_id}: {e}")

    return {
        "migrated_count": migrated,
        "skipped_count": skipped,
        "failed_count": failed,
        "total_entities": total_entities,
    }

import json
from pathlib import Path
from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


def parse_document(doc_id: str, text: str) -> dict:
    """Parse document using Docling to extract structure: headings, tables, lists, paragraphs."""
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        logger.warning(f"Docling not installed; skipping structured parsing for {doc_id}")
        return {"document_id": doc_id, "title": "", "sections": [], "parsed_at": datetime.now(timezone.utc).isoformat()}

    upload_dir = settings.uploads_dir / doc_id
    files = list(upload_dir.iterdir()) if upload_dir.exists() else []
    file_path = files[0] if files else upload_dir

    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    doc = result.document

    parsed = {
        "document_id": doc_id,
        "title": doc.metadata.title if doc.metadata else "",
        "sections": [],
        "parsed_at": datetime.now(timezone.utc).isoformat(),
    }

    for idx, section in enumerate(doc.iterate_sections()):
        sec_data = {
            "section_id": f"{doc_id}_s{idx}",
            "heading": section.heading if hasattr(section, "heading") else "",
            "level": section.level if hasattr(section, "level") else 1,
            "page": section.bbox.page if hasattr(section, "bbox") else None,
            "paragraphs": [],
            "tables": [],
        }

        for para in section.iterate_paragraphs():
            sec_data["paragraphs"].append(para.text.strip())

        for table in section.iterate_tables():
            table_data = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_data.append(row_data)
            sec_data["tables"].append(table_data)

        parsed["sections"].append(sec_data)

    output_dir = settings.processed_dir / doc_id
    output_dir.mkdir(parents=True, exist_ok=True)
    parse_path = output_dir / "parsed_output.json"

    with open(parse_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2, default=str)

    conn = get_connection()
    conn.execute(
        "UPDATE documents SET processing_status = ? WHERE id = ?",
        ("parsing_complete", doc_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Parsing complete for {doc_id}: {len(parsed['sections'])} sections")
    return parsed

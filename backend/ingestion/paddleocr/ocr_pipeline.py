import json
from pathlib import Path
from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


def run_ocr(doc_id: str, file_path: Path) -> dict:
    """
    Extract text from scanned documents using PaddleOCR.
    Returns OCR result with text, confidence scores, and page data.
    """
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        logger.warning(f"PaddleOCR not installed; skipping OCR for {doc_id}")
        return {"document_id": doc_id, "pages": [], "total_text": "", "avg_confidence": 0.0, "processed_at": datetime.now(timezone.utc).isoformat()}

    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    result = ocr.ocr(str(file_path), cls=True)

    ocr_data = {
        "document_id": doc_id,
        "pages": [],
        "total_text": "",
        "avg_confidence": 0.0,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    total_conf = 0
    total_boxes = 0

    if isinstance(result, list) and result:
        for page_idx, page_result in enumerate(result):
            page_text = []
            page_confidence = []

            if page_result:
                for line in page_result:
                    bbox, text_info = line
                    text = text_info[0]
                    conf = text_info[1]
                    page_text.append(text)
                    page_confidence.append(conf)

            page_text_str = " ".join(page_text)
            avg_page_conf = sum(page_confidence) / len(page_confidence) if page_confidence else 0

            ocr_data["pages"].append({
                "page_number": page_idx + 1,
                "text": page_text_str,
                "confidence": round(avg_page_conf, 4),
                "box_count": len(page_text),
            })

            total_conf += sum(page_confidence)
            total_boxes += len(page_confidence)

    ocr_data["avg_confidence"] = round(total_conf / total_boxes, 4) if total_boxes else 0
    ocr_data["total_text"] = "\n\n".join(p["text"] for p in ocr_data["pages"])

    output_dir = settings.processed_dir / doc_id
    output_dir.mkdir(parents=True, exist_ok=True)
    ocr_output_path = output_dir / "ocr_output.json"

    with open(ocr_output_path, "w", encoding="utf-8") as f:
        json.dump(ocr_data, f, ensure_ascii=False, indent=2)

    conn = get_connection()
    metadata = json.dumps({
        "ocr_avg_confidence": ocr_data["avg_confidence"],
        "ocr_pages": len(ocr_data["pages"]),
        "ocr_output_path": str(ocr_output_path),
    })
    conn.execute(
        "UPDATE documents SET processing_status = ?, metadata = ? WHERE id = ?",
        ("ocr_complete", metadata, doc_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"OCR complete for {doc_id}: {len(ocr_data['pages'])} pages, avg conf {ocr_data['avg_confidence']:.2%}")
    return ocr_data

import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from backend.logging_config import logger


def detect_document_type(file_path: Path, file_type: str) -> dict:
    """
    Analyze document and return:
    - needs_ocr: bool
    - page_count: int
    - text_summary: first 500 chars of text if searchable
    - has_images: bool
    """
    result = {
        "needs_ocr": False,
        "page_count": 0,
        "has_text": False,
        "text_sample": "",
        "detection_method": "unknown",
    }

    if file_type == "application/pdf":
        return _analyze_pdf(file_path)
    elif file_type in ("image/jpeg", "image/png", "image/tiff"):
        result["needs_ocr"] = True
        result["detection_method"] = "image_always_ocr"
        result["page_count"] = 1
        return result
    elif file_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "text/plain",
        "message/rfc822",
        "application/vnd.ms-outlook",
    ):
        result["needs_ocr"] = False
        result["has_text"] = True
        result["detection_method"] = "native_format"
        result["page_count"] = 1
        return result

    return result


def _analyze_pdf(file_path: Path) -> dict:
    result = {
        "needs_ocr": False,
        "page_count": 0,
        "has_text": False,
        "text_sample": "",
        "detection_method": "unknown",
    }

    try:
        doc = fitz.open(str(file_path))
        result["page_count"] = len(doc)

        text_pages = 0
        total_text = ""

        for page in doc:
            text = page.get_text().strip()
            if len(text) > 20:
                text_pages += 1
                total_text += text[:1000]

        doc.close()

        if text_pages == 0:
            result["needs_ocr"] = True
            result["detection_method"] = "no_text_layer"
        elif text_pages < result["page_count"]:
            result["needs_ocr"] = True
            result["has_text"] = True
            result["detection_method"] = "partial_text"
            result["text_sample"] = total_text[:500]
        else:
            result["needs_ocr"] = False
            result["has_text"] = True
            result["detection_method"] = "full_text"
            result["text_sample"] = total_text[:500]

        logger.info(
            f"PDF analysis: {result['page_count']} pages, "
            f"{text_pages} with text, needs_ocr={result['needs_ocr']}"
        )

    except Exception as e:
        logger.error(f"PDF analysis failed: {e}")
        result["needs_ocr"] = True
        result["detection_method"] = "analysis_failed"

    return result


def extract_native_text(file_path: Path) -> str:
    """Extract text from searchable PDFs using PyMuPDF."""
    try:
        doc = fitz.open(str(file_path))
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"Native text extraction failed: {e}")
        return ""

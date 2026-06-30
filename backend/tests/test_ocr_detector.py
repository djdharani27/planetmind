import pytest
from pathlib import Path
from backend.ingestion.ocr_detector import detect_document_type


class TestOCRDetection:
    def test_image_always_needs_ocr(self):
        result = detect_document_type(Path("test.jpg"), "image/jpeg")
        assert result["needs_ocr"] is True
        assert result["detection_method"] == "image_always_ocr"
        assert result["page_count"] == 1

    def test_png_always_needs_ocr(self):
        result = detect_document_type(Path("test.png"), "image/png")
        assert result["needs_ocr"] is True
        assert result["page_count"] == 1

    def test_docx_no_ocr(self):
        result = detect_document_type(Path("test.docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert result["needs_ocr"] is False
        assert result["has_text"] is True
        assert result["detection_method"] == "native_format"

    def test_unknown_type(self):
        result = detect_document_type(Path("test.bin"), "application/octet-stream")
        assert result["needs_ocr"] is False
        assert result["detection_method"] == "unknown"

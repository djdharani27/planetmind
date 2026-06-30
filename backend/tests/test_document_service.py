import pytest
import json
from backend.models.document import validate_file_type, validate_file_size, ALLOWED_TYPES, MAX_FILE_SIZE


class TestFileValidation:
    def test_validate_pdf_type(self):
        assert validate_file_type("application/pdf") == "pdf"

    def test_validate_docx_type(self):
        assert validate_file_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document") == "docx"

    def test_validate_jpg_type(self):
        assert validate_file_type("image/jpeg") == "jpg"

    def test_validate_png_type(self):
        assert validate_file_type("image/png") == "png"

    def test_reject_unknown_type(self):
        assert validate_file_type("text/html") is None
        assert validate_file_type("application/zip") is None

    def test_validate_valid_size(self):
        assert validate_file_size(1000) is True
        assert validate_file_size(MAX_FILE_SIZE) is True

    def test_reject_zero_size(self):
        assert validate_file_size(0) is False

    def test_reject_oversize(self):
        assert validate_file_size(MAX_FILE_SIZE + 1) is False

    def test_allowed_types_structure(self):
        valid_exts = ("pdf", "docx", "jpg", "png", "csv", "xlsx", "xls", "eml", "msg", "txt", "tiff")
        for mime, ext in ALLOWED_TYPES.items():
            assert "/" in mime
            assert ext in valid_exts


class TestDocumentResponse:
    def test_document_response_from_dict(self):
        from backend.models.document import DocumentResponse
        doc = DocumentResponse(
            id="test-123",
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            upload_timestamp="2024-01-01T00:00:00",
            processing_status="uploaded",
            storage_path="/tmp/test.pdf",
            metadata={},
        )
        assert doc.id == "test-123"
        assert doc.processing_status == "uploaded"


class TestErrorResponse:
    def test_error_response(self):
        from backend.models.document import ErrorResponse
        err = ErrorResponse(status="error", message="Something went wrong")
        assert err.status == "error"

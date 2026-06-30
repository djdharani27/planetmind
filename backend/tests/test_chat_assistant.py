import pytest
from backend.llm.chat_assistant import build_context, generate_answer, _fallback_answer


class TestChatAssistant:
    def test_build_context_from_results(self):
        results = [
            {
                "source": "vector",
                "document_id": "doc-1",
                "filename": "maintenance.pdf",
                "page_number": 5,
                "snippet": "The pump bearing failed due to overheating.",
                "score": 0.92,
            },
            {
                "source": "bm25",
                "document_id": "doc-2",
                "filename": "inspection.pdf",
                "page_number": 12,
                "snippet": "Inspection revealed contamination.",
                "score": 0.85,
            },
        ]
        context = build_context(results)
        assert "maintenance.pdf" in context
        assert "inspection.pdf" in context
        assert "bearing failed" in context

    def test_build_context_empty(self):
        assert build_context([]) == ""

    def test_fallback_answer_with_results(self):
        results = [
            {"snippet": "The pump P-204 experienced a bearing failure on March 14."}
        ]
        answer = _fallback_answer("Why did pump fail?", results)
        assert "P-204" in answer

    def test_fallback_answer_no_results(self):
        answer = _fallback_answer("Why did pump fail?", [])
        assert "couldn't find" in answer.lower()

    def test_generate_answer_without_llm(self):
        results = [
            {
                "source": "vector",
                "document_id": "doc-1",
                "filename": "report.pdf",
                "page_number": 3,
                "snippet": "Gearbox inspection revealed misalignment.",
                "score": 0.9,
            }
        ]
        answer = generate_answer("What caused the failure?", results)
        assert answer["question"] == "What caused the failure?"
        assert len(answer["sources"]) == 1
        assert answer["sources"][0]["filename"] == "report.pdf"
        assert 0 <= answer["confidence"] <= 100

    def test_confidence_no_results(self):
        answer = generate_answer("test", [])
        assert answer["confidence"] < 50

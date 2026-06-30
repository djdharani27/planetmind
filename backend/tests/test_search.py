import pytest
from backend.search.hybrid_search import _merge_and_rerank


class TestSearchMerge:
    def test_deduplicate_by_doc_id(self):
        results = [
            {"document_id": "a", "score": 0.9, "snippet": "first"},
            {"document_id": "a", "score": 0.8, "snippet": "first dup"},
            {"document_id": "b", "score": 0.7, "snippet": "second"},
            {"document_id": "c", "score": 0.5, "snippet": "third"},
        ]
        merged = _merge_and_rerank("test query", results, top_k=5)
        doc_ids = [r["document_id"] for r in merged]
        assert len(doc_ids) == 3
        assert "a" in doc_ids
        assert "b" in doc_ids
        assert "c" in doc_ids

    def test_merge_sorts_by_score(self):
        results = [
            {"document_id": "low", "score": 0.1, "snippet": "low score"},
            {"document_id": "high", "score": 0.95, "snippet": "high score"},
            {"document_id": "mid", "score": 0.5, "snippet": "mid score"},
        ]
        merged = _merge_and_rerank("test", results, top_k=3)
        assert merged[0]["score"] >= merged[1]["score"] >= merged[2]["score"]

    def test_top_k_truncation(self):
        results = [
            {"document_id": str(i), "score": 1.0 - i * 0.1, "snippet": f"doc {i}"}
            for i in range(20)
        ]
        merged = _merge_and_rerank("test", results, top_k=5)
        assert len(merged) <= 5

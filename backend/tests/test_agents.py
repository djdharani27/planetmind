import pytest
from backend.llm.maintenance_rca import _fallback_rca


class TestMaintenanceRCA:
    def test_fallback_rca_structure(self):
        result = _fallback_rca("pump failure", [
            {"document_id": "doc1", "snippet": "Bearing failure in Pump P-204 due to lubrication contamination"}
        ])
        assert "root_causes" in result
        assert "predictive_recommendations" in result
        assert "failure_patterns" in result
        assert result["overall_confidence"] > 0

    def test_fallback_rca_empty_results(self):
        result = _fallback_rca("unknown", [])
        assert len(result["root_causes"]) > 0

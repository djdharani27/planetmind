import pytest
from backend.llm.entity_extractor import _regex_extract


class TestRegexEntityExtraction:
    def test_extract_equipment(self):
        text = "Pump P-204 failed on 2024-03-14. Inspection under Factory Act compliance."
        entities = _regex_extract(text)
        equipment = [e for e in entities if e["type"] == "equipment"]
        assert len(equipment) >= 1
        assert any("Pump P-204" in e["value"] for e in equipment)

    def test_extract_dates(self):
        text = "Failure occurred on 2024-03-14 and was resolved on 2024-03-15."
        entities = _regex_extract(text)
        dates = [e for e in entities if e["type"] == "date"]
        assert len(dates) >= 1
        assert any("2024-03-14" in e["value"] for e in dates)

    def test_extract_regulations(self):
        text = "Refer to Factory Act and OISD standards. Also ISO 9001 applies."
        entities = _regex_extract(text)
        regs = [e for e in entities if e["type"] == "regulation"]
        assert len(regs) >= 2

    def test_extract_process_parameters(self):
        text = "Pressure measured at 150 bar with temperature of 350°C."
        entities = _regex_extract(text)
        params = [e for e in entities if e["type"] == "process_parameter"]
        assert len(params) >= 1

    def test_empty_text(self):
        entities = _regex_extract("")
        assert entities == []

    def test_no_entities(self):
        text = "Nothing relevant here."
        entities = _regex_extract(text)
        assert entities == []

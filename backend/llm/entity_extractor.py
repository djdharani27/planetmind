import json
import re
from pathlib import Path
from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


ENTITY_TYPES = [
    "equipment",
    "component",
    "failure",
    "maintenance_activity",
    "technician",
    "date",
    "location",
    "regulation",
    "document",
    "process_parameter",
]

EXTRACTION_PROMPT = """Extract industrial entities from the following document text. 
Return JSON with these entity types: {types}

Rules:
- equipment: equipment identifiers like Pump P-204, Turbine WTG-12
- component: sub-components like bearing, seal, gearbox
- failure: failure modes like bearing failure, overheating
- maintenance_activity: actions like replacement, inspection, calibration
- technician: person names
- date: dates found in text (ISO format)
- location: physical locations
- regulation: regulatory references like Factory Act, OISD
- document: referenced documents
- process_parameter: measurements like pressure, temperature

Text:
{text}

Return ONLY valid JSON: {{"entities": [{{"type": "...", "value": "...", "context": "...", "confidence": 0.0-1.0}}]}}"""


def extract_entities(doc_id: str, text: str, llm_client=None) -> list[dict]:
    """Extract entities using LLM or fallback to regex patterns."""
    entities = []

    if llm_client:
        entities = _llm_extract(llm_client, text)
    else:
        entities = _regex_extract(text)

    output_dir = settings.processed_dir / doc_id
    output_dir.mkdir(parents=True, exist_ok=True)
    entities_path = output_dir / "entities.json"

    with open(entities_path, "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    conn = get_connection()
    conn.execute(
        "UPDATE documents SET processing_status = ? WHERE id = ?",
        ("entities_complete", doc_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Entity extraction complete for {doc_id}: {len(entities)} entities")
    return entities


def _llm_extract(client, text: str) -> list[dict]:
    if len(text) > 8000:
        text = text[:8000] + "..."
    prompt = EXTRACTION_PROMPT.format(types=", ".join(ENTITY_TYPES), text=text)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        return data.get("entities", [])
    except json.JSONDecodeError:
        return _regex_extract(text)


def _regex_extract(text: str) -> list[dict]:
    entities = []
    patterns = {
        "equipment": r"\b(Pump|Turbine|Motor|Generator|Compressor|Valve|Transformer)\s+[A-Z]{1,3}[-]\d{2,5}\b",
        "date": r"\b\d{4}[-/]\d{2}[-/]\d{2}\b",
        "regulation": r"\b(Factory\s+Act|OISD|PESO|ISO\s+\d+|API\s+\d+)\b",
        "process_parameter": r"\b(\d+(?:\.\d+)?\s*(bar|psi|kPa|°C|°F|RPM|Hz|volts|amps))\b",
    }
    for entity_type, pattern in patterns.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            entities.append({
                "type": entity_type,
                "value": match.group(),
                "context": text[start:end].strip(),
                "confidence": 0.85,
            })
    return entities

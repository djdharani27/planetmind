"""Graph search — searches entity knowledge graph built from processed documents.

Entities are stored as JSON files on disk (storage/processed/*/entities.json).
The search matches query tokens against entity values and types,
returning document-level results with relevance scores.
"""

import json
from pathlib import Path
from collections import defaultdict
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


def search_graph(query: str, top_k: int = 8) -> list[dict]:
    """Search the entity knowledge graph for documents matching the query.

    Args:
        query: Natural language search query.
        top_k: Maximum number of results to return.

    Returns:
        List of result dicts with document_id, filename, snippet, and score.
    """
    query_lower = query.lower().strip()
    query_tokens = set(query_lower.split())

    if not query_tokens:
        return []

    proc_dir: Path = settings.processed_dir
    if not proc_dir.exists():
        return []

    # Map document IDs to filenames from the database
    docs = {}
    try:
        conn = get_connection()
        rows = conn.execute("SELECT id, filename FROM documents").fetchall()
        conn.close()
        for r in rows:
            docs[r["id"]] = r["filename"]
    except Exception as e:
        logger.warning(f"Graph search: failed to load document names: {e}")

    # Gather all entities grouped by document
    doc_entities: dict[str, list[dict]] = defaultdict(list)
    for child in sorted(proc_dir.iterdir()):
        if not child.is_dir():
            continue
        ep = child / "entities.json"
        if not ep.exists():
            continue
        doc_id = child.name
        try:
            entities = json.loads(ep.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(entities, list):
            continue
        doc_entities[doc_id].extend(entities)

    if not doc_entities:
        return []

    # Score each document based on entity matches
    scored: list[tuple[float, str, str]] = []  # (score, doc_id, snippet)

    for doc_id, entities in doc_entities.items():
        matched_entities = []
        total_score = 0.0

        for ent in entities:
            etype = (ent.get("type") or "").strip().lower()
            evalue = (ent.get("value") or "").strip().lower()
            if not etype or not evalue:
                continue

            # Score based on match quality
            evalue_lower = evalue.lower()
            etype_lower = etype.lower()

            # Exact value match (highest)
            if query_lower == evalue_lower:
                score = 1.0
            # Query contains entity value
            elif query_lower in evalue_lower or evalue_lower in query_lower:
                score = 0.8
            # Token-level match
            else:
                evalue_tokens = set(evalue_lower.split())
                common = query_tokens & evalue_tokens
                if common:
                    score = 0.6 * (len(common) / max(len(query_tokens), len(evalue_tokens)))
                # Type match (lowest — e.g. query mentioning "bearing" matches component type)
                elif any(t in etype_lower for t in query_tokens) or any(etype_lower in t for t in query_tokens):
                    score = 0.3
                else:
                    continue

            total_score += score
            matched_entities.append(f"[{etype.title()}] {ent.get('value', '')}")

        if matched_entities:
            filename = docs.get(doc_id, doc_id[:8])
            snippet = "; ".join(matched_entities[:10])
            scored.append((total_score, doc_id, filename, snippet))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, doc_id, filename, snippet in scored[:top_k]:
        results.append({
            "source": "graph",
            "document_id": doc_id,
            "filename": filename,
            "score": score,
            "snippet": snippet,
        })

    return results

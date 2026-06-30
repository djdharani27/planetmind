from backend.config import settings
from backend.logging_config import logger


def search_graph(query: str, top_k: int = 10) -> list[dict]:
    """Search Neo4j knowledge graph for entities matching query, return connected documents."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=5,
        )
        with driver.session() as session:
            result = session.run(
                """MATCH (d:Document)-[:MENTIONS]->(e)
                   WHERE toLower(e.value) CONTAINS toLower($query)
                      OR toLower(e.value) IN split(toLower($query), ' ')
                   WITH d, count(e) AS matches
                   RETURN d.id AS document_id, matches
                   ORDER BY matches DESC
                   LIMIT $top_k""",
                query=query,
                top_k=top_k,
            )
            records = list(result)
        driver.close()

        results = []
        for rec in records:
            results.append({
                "source": "graph",
                "document_id": rec["document_id"],
                "score": float(rec["matches"]) / max(top_k, 1),
                "snippet": _get_document_snippet(rec["document_id"]),
            })
        return results
    except Exception as e:
        logger.info(f"Graph search unavailable (Neo4j may not be running): {e}")
        return []


def _get_document_snippet(doc_id: str) -> str:
    import json
    ocr_file = settings.processed_dir / doc_id / "ocr_output.json"
    if ocr_file.exists():
        with open(ocr_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("total_text", "")[:300]
    return ""

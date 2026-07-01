"""Neo4j knowledge graph search — returns entities matching query + connected context."""

from backend.config import settings
from backend.logging_config import logger


def search_graph(query: str, top_k: int = 10) -> list[dict]:
    """Search Neo4j for entities matching query, return connected documents and entity context."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=5,
        )
        with driver.session() as session:
            # Find matching entities and their connected docs + related entities
            result = session.run(
                """MATCH (e)
                   WHERE toLower(e.value) CONTAINS toLower($query)
                   OPTIONAL MATCH (d:Document)-[:MENTIONS]->(e)
                   OPTIONAL MATCH (e)-[r]-(related)
                   WHERE related:Equipment OR related:Failure OR related:MaintenanceActivity
                      OR related:Component OR related:Technician OR related:Location
                   WITH e, labels(e) AS types, collect(DISTINCT d.id) AS doc_ids,
                        collect(DISTINCT {entity: related.value, type: head(labels(related))}) AS related_entities
                   RETURN e.value AS entity_value,
                          head(types) AS entity_type,
                          doc_ids,
                          related_entities
                   LIMIT $top_k""",
                parameters={"query": query, "top_k": top_k},
            )
            records = list(result)
        driver.close()

        results = []
        for rec in records:
            entity_value = rec["entity_value"]
            entity_type = rec["entity_type"]
            doc_ids = rec["doc_ids"] or []
            related = rec["related_entities"] or []

            # Build a rich snippet from entity + related context
            context_parts = [f"{entity_type}: {entity_value}"]
            for rel in related:
                if rel.get("entity"):
                    context_parts.append(f"  → {rel['type']}: {rel['entity']}")
            snippet = "\n".join(context_parts[:6])

            for doc_id in doc_ids:
                results.append({
                    "source": "graph",
                    "document_id": doc_id,
                    "score": 0.8 + (0.2 / max(len(doc_ids), 1)),  # entity match = high relevance
                    "snippet": snippet,
                    "entity": entity_value,
                    "entity_type": entity_type,
                    "related_entities": [r["entity"] for r in related if r.get("entity")],
                })

        return results[:top_k]
    except Exception as e:
        logger.info(f"Graph search unavailable (Neo4j may not be running): {e}")
        return []

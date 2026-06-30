from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


def build_knowledge_graph(doc_id: str, entities: list[dict]) -> dict:
    """Build knowledge graph in Neo4j from extracted entities."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        logger.warning("Neo4j driver not installed; skipping graph construction")
        return {"nodes": 0, "relationships": 0}

    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))

    nodes_created = 0
    rels_created = 0

    with driver.session() as session:
        session.run("MERGE (d:Document {id: $id, filename: ''})", id=doc_id)

        for entity in entities:
            entity_type = entity.get("type", "unknown")
            value = entity.get("value", "").strip()
            if not value or len(value) < 2:
                continue

            label = entity_type.replace("_", " ").title().replace(" ", "")
            session.run(
                f"MERGE (e:{label} {{value: $value}}) MERGE (d:Document {{id: $doc_id}}) MERGE (d)-[:MENTIONS]->(e)",
                value=value,
                doc_id=doc_id,
            )
            nodes_created += 1

        _build_equipment_relationships(session, entities, doc_id)

    driver.close()

    conn = get_connection()
    conn.execute(
        "UPDATE documents SET processing_status = ? WHERE id = ?",
        ("graph_complete", doc_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Knowledge graph built for {doc_id}: {nodes_created} nodes, {rels_created} rels")
    return {"nodes": nodes_created, "relationships": rels_created}


def _build_equipment_relationships(session, entities: list[dict], doc_id: str):
    """Link equipment to failures and activities."""
    equipment = [e["value"] for e in entities if e["type"] == "equipment"]
    failures = [e["value"] for e in entities if e["type"] == "failure"]
    activities = [e["value"] for e in entities if e["type"] == "maintenance_activity"]
    technicians = [e["value"] for e in entities if e["type"] == "technician"]

    for eq in equipment:
        for fail in failures:
            session.run(
                "MATCH (e:Equipment {value: $eq}) MATCH (f:Failure {value: $fail}) MERGE (e)-[:HAS_FAILURE]->(f)",
                eq=eq, fail=fail,
            )

    for fail in failures:
        for tech in technicians:
            session.run(
                "MATCH (f:Failure {value: $fail}) MATCH (t:Technician {value: $tech}) MERGE (f)-[:FIXED_BY]->(t)",
                fail=fail, tech=tech,
            )

    for act in activities:
        session.run(
            "MATCH (a:MaintenanceActivity {value: $act}) MATCH (d:Document {id: $doc_id}) MERGE (a)-[:RECORDED_IN]->(d)",
            act=act, doc_id=doc_id,
        )

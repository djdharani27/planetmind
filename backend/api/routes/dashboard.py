from fastapi import APIRouter
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _get_neo4j_connection():
    try:
        from neo4j import GraphDatabase
        return GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=3,
        )
    except ImportError:
        return None


@router.get("")
async def dashboard():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]
    ready = conn.execute("SELECT COUNT(*) as c FROM documents WHERE processing_status = 'ready'").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) as c FROM documents WHERE processing_status = 'failed'").fetchone()["c"]
    processing = conn.execute("SELECT COUNT(*) as c FROM documents WHERE processing_status = 'processing'").fetchone()["c"]
    by_status = conn.execute(
        "SELECT processing_status, COUNT(*) as c FROM documents GROUP BY processing_status"
    ).fetchall()
    conn.close()

    graph_nodes = 0
    graph_rels = 0
    try:
        driver = _get_neo4j_connection()
        if driver:
            with driver.session() as session:
                nodes_result = session.run("MATCH (n) RETURN count(n) AS cnt").single()
                rels_result = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()
                graph_nodes = nodes_result["cnt"] if nodes_result else 0
                graph_rels = rels_result["cnt"] if rels_result else 0
            driver.close()
    except Exception:
        pass

    vector_count = 0
    try:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=3)
        info = qdrant.get_collection("planetmind_chunks")
        vector_count = info.points_count if info else 0
    except Exception:
        pass

    return {
        "total_documents": total,
        "documents_ready": ready,
        "documents_processing": processing,
        "documents_failed": failed,
        "graph_nodes": graph_nodes,
        "graph_relationships": graph_rels,
        "vector_count": vector_count,
        "processing_success_rate": round((ready / total * 100) if total else 0, 1),
        "by_status": {r["processing_status"]: r["c"] for r in by_status},
    }


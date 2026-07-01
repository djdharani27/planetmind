from fastapi import APIRouter
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger
import shutil

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/nuke")
async def nuke_everything():
    """Delete everything: all documents, SQLite data, storage files, Qdrant vectors, Neo4j graph."""

    results = {
        "sqlite_documents": 0,
        "storage_deleted": False,
        "qdrant_cleared": False,
        "neo4j_cleared": False,
    }

    # 1. Delete all documents from SQLite
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]
    conn.execute("DELETE FROM documents")
    conn.commit()
    conn.close()
    results["sqlite_documents"] = count
    logger.info(f"Nuke: deleted {count} documents from SQLite")

    # 2. Wipe storage dirs (uploads + processed + cache)
    for d in [settings.uploads_dir, settings.processed_dir, settings.cache_dir]:
        if d.exists():
            shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)
    results["storage_deleted"] = True
    logger.info("Nuke: wiped storage directories")

    # 3. Clear Qdrant collection
    try:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=5)
        qdrant.delete_collection("planetmind_chunks")
        logger.info("Nuke: deleted Qdrant collection planetmind_chunks")
    except Exception as e:
        logger.warning(f"Nuke: Qdrant clear failed — {e}")

    results["qdrant_cleared"] = True

    # 4. Clear Neo4j graph
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=5,
        )
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        driver.close()
        logger.info("Nuke: deleted all Neo4j nodes and relationships")
    except Exception as e:
        logger.warning(f"Nuke: Neo4j clear failed — {e}")

    results["neo4j_cleared"] = True

    logger.info(f"Nuke complete: {results}")
    return {"status": "nuked", "details": results}

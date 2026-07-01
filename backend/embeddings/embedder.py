import json
from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


def generate_and_store_embeddings(doc_id: str, chunks: list[dict]) -> int:
    """Generate embeddings using BGE-M3 and store in Qdrant."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
    except ImportError:
        logger.warning("Embedding dependencies not installed; skipping embedding generation")
        return 0

    # Use the cached model from hybrid_search to avoid reloading per document
    from backend.search.hybrid_search import _get_bge_model
    model = _get_bge_model()

    try:
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60, check_compatibility=False)
    except Exception as e:
        logger.warning(f"Qdrant connection failed for {doc_id}: {e}")
        return 0
    collection_name = "planetmind_chunks"

    try:
        existing = qdrant.get_collections()
        if collection_name not in [c.name for c in existing.collections]:
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
    except Exception as e:
        logger.warning(f"Qdrant setup failed for {doc_id}: {e}")
        return 0

    texts = [c["chunk_text"] for c in chunks]
    embeddings = model.encode(texts, batch_size=32)

    points = []
    for i, chunk in enumerate(chunks):
        emb = embeddings["dense_vecs"][i].tolist()
        # Use a deterministic unique ID from the chunk_id to prevent collisions
        point_id = abs(hash(chunk["chunk_id"])) % (2**63)
        points.append(PointStruct(
            id=point_id,
            vector=emb,
            payload={
                "chunk_id": chunk["chunk_id"],
                "document_id": doc_id,
                "page_number": chunk["page_number"],
                "section": chunk["section"],
                "text": chunk["chunk_text"],
                "equipment_tags": chunk.get("equipment_tags", []),
            },
        ))

    try:
        qdrant.upsert(collection_name=collection_name, points=points)
    except Exception as e:
        logger.warning(f"Qdrant upsert failed for {doc_id}: {e}")
        return 0

    conn = get_connection()
    conn.execute(
        "UPDATE documents SET processing_status = ? WHERE id = ?",
        ("embeddings_complete", doc_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Embeddings stored for {doc_id}: {len(points)} vectors in Qdrant")
    return len(points)

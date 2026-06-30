import json
from datetime import datetime, timezone
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger


def generate_and_store_embeddings(doc_id: str, chunks: list[dict]) -> int:
    """Generate embeddings using BGE-M3 and store in Qdrant."""
    try:
        from FlagEmbedding import BGEM3FlagModel
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
    except ImportError:
        logger.warning("Embedding dependencies not installed; skipping embedding generation")
        return 0

    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    try:
        qdrant = QdrantClient(host="localhost", port=6333)
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
        points.append(PointStruct(
            id=i,
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

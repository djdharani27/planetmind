from datetime import datetime, timezone
from backend.logging_config import logger


def hybrid_search(query: str, top_k: int = 10) -> dict:
    """Parallel search across BM25, Qdrant vector, and Neo4j graph."""
    bm25_results = _bm25_search(query, top_k)
    vector_results = _vector_search(query, top_k)
    graph_results = _graph_search(query, top_k)

    merged = _merge_and_rerank(query, bm25_results + vector_results + graph_results, top_k)

    return {
        "query": query,
        "results": merged,
        "source_breakdown": {
            "bm25": len(bm25_results),
            "vector": len(vector_results),
            "graph": len(graph_results),
        },
        "searched_at": datetime.now(timezone.utc).isoformat(),
    }


def _bm25_search(query: str, top_k: int) -> list[dict]:
    try:
        from rank_bm25 import BM25Okapi
        from backend.database.database import get_connection

        conn = get_connection()
        rows = conn.execute("SELECT id, filename, metadata FROM documents WHERE processing_status = 'ready'").fetchall()
        conn.close()

        if not rows:
            return []

        corpus = [_extract_text_from_meta(r["metadata"]) for r in rows]
        tokenized_corpus = [doc.split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.split()
        scores = bm25.get_scores(tokenized_query)

        results = []
        for i, score in enumerate(scores):
            if score > 0:
                r = dict(rows[i])
                results.append({
                    "source": "bm25",
                    "document_id": r["id"],
                    "filename": r["filename"],
                    "score": float(score),
                    "snippet": corpus[i][:200],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    except ImportError:
        return []


def _vector_search(query: str, top_k: int) -> list[dict]:
    try:
        from FlagEmbedding import BGEM3FlagModel
        from qdrant_client import QdrantClient

        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        qemb = model.encode([query], batch_size=1)["dense_vecs"][0].tolist()

        qdrant = QdrantClient(host="localhost", port=6333)
        results = qdrant.search(
            collection_name="planetmind_chunks",
            query_vector=qemb,
            limit=top_k,
        )

        return [{
            "source": "vector",
            "document_id": r.payload.get("document_id", ""),
            "chunk_id": r.payload.get("chunk_id", ""),
            "score": float(r.score),
            "snippet": r.payload.get("text", "")[:200],
            "page_number": r.payload.get("page_number", 1),
        } for r in results]
    except Exception:
        return []


def _graph_search(query: str, top_k: int) -> list[dict]:
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        with driver.session() as session:
            query_lower = query.lower()
            result = session.run(
                """MATCH (n)
                   WHERE any(label IN labels(n) WHERE toLower(label) CONTAINS $term)
                      OR toLower(n.value) CONTAINS $term
                   MATCH (n)-[:MENTIONS]->(d:Document)
                   RETURN n.value AS entity, labels(n) AS type, d.id AS doc_id
                   LIMIT $limit""",
                term=query_lower,
                limit=top_k * 2,
            )
            records = list(result)

        driver.close()

        seen = set()
        graph_results = []
        for r in records:
            key = f"{r['entity']}_{r['doc_id']}"
            if key not in seen:
                seen.add(key)
                graph_results.append({
                    "source": "graph",
                    "document_id": r["doc_id"],
                    "entity": r["entity"],
                    "entity_type": r["type"][0] if r["type"] else "",
                    "score": 0.75,
                    "snippet": f"Entity: {r['entity']} ({', '.join(r['type'])})",
                })

        return graph_results[:top_k]
    except Exception:
        return []


def _merge_and_rerank(query: str, results: list[dict], top_k: int) -> list[dict]:
    seen_ids = set()
    deduplicated = []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        if r["document_id"] not in seen_ids:
            seen_ids.add(r["document_id"])
            deduplicated.append(r)

    try:
        from FlagEmbedding import FlagReranker
        reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
        pairs = [(query, r["snippet"]) for r in deduplicated]
        rerank_scores = reranker.compute_score(pairs)
        for i, r in enumerate(deduplicated):
            r["rerank_score"] = float(rerank_scores[i]) if isinstance(rerank_scores, list) else float(rerank_scores)
        deduplicated.sort(key=lambda x: x.get("rerank_score", x["score"]), reverse=True)
    except Exception:
        for r in deduplicated:
            r["rerank_score"] = r["score"]

    return deduplicated[:top_k]


def _extract_text_from_meta(metadata_str: str) -> str:
    import json
    try:
        meta = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
        return meta.get("ocr_text", "")[:1000]
    except Exception:
        return ""

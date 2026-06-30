from datetime import datetime, timezone
from pathlib import Path
import json
from backend.config import settings
from backend.logging_config import logger


def hybrid_search(query: str, top_k: int = 10) -> dict:
    bm25_results = _bm25_search(query, top_k)
    vector_results = _vector_search(query, top_k)
    graph_results = _graph_search(query, top_k)

    all_results = bm25_results + vector_results + graph_results
    merged = _merge_and_rerank(query, all_results, top_k)

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

        processed = settings.processed_dir
        corpus = []
        doc_ids = []

        for doc_dir in processed.iterdir():
            if not doc_dir.is_dir():
                continue
            ocr_file = doc_dir / "ocr_output.json"
            if ocr_file.exists():
                try:
                    with open(ocr_file, encoding="utf-8") as f:
                        data = json.load(f)
                    text = data.get("total_text", "")
                    if text.strip():
                        corpus.append(text)
                        doc_ids.append(doc_dir.name)
                except Exception:
                    pass

        if not corpus:
            return []

        tokenized_corpus = [doc.split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.split()
        scores = bm25.get_scores(tokenized_query)

        results = []
        for i, score in enumerate(scores):
            if score > 0:
                results.append({
                    "source": "bm25",
                    "document_id": doc_ids[i],
                    "filename": doc_ids[i],
                    "score": float(score),
                    "snippet": corpus[i][:300],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    except Exception as e:
        logger.warning(f"BM25 search failed: {e}")
        return []


def _merge_and_rerank(query: str, results: list[dict], top_k: int) -> list[dict]:
    seen_ids = set()
    deduplicated = []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        if r.get("document_id") not in seen_ids:
            seen_ids.add(r["document_id"])
            r["rerank_score"] = r["score"]
            deduplicated.append(r)
    return deduplicated[:top_k]


def _vector_search(query: str, top_k: int) -> list[dict]:
    try:
        from FlagEmbedding import BGEM3FlagModel
        from qdrant_client import QdrantClient

        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=5)

        query_embedding = model.encode([query], batch_size=1)
        query_vec = query_embedding["dense_vecs"][0].tolist()

        hits = qdrant.search(
            collection_name="planetmind_chunks",
            query_vector=query_vec,
            limit=top_k,
        )

        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append({
                "source": "vector",
                "document_id": payload.get("document_id", ""),
                "chunk_id": payload.get("chunk_id", ""),
                "score": float(hit.score),
                "snippet": payload.get("text", "")[:300],
                "page_number": payload.get("page_number", 1),
                "equipment_tags": payload.get("equipment_tags", []),
            })
        return results
    except Exception as e:
        logger.info(f"Vector search unavailable: {e}")
        return []


def _graph_search(query: str, top_k: int) -> list[dict]:
    try:
        from backend.graph.graph_searcher import search_graph
        return search_graph(query, top_k)
    except Exception as e:
        logger.info(f"Graph search unavailable: {e}")
        return []

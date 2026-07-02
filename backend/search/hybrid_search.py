"""Hybrid search — BM25 + Vector (BGE-M3 → Qdrant) + Graph (Neo4j).

Models are cached at module level so they load once, not per-query.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
from backend.config import settings
from backend.logging_config import logger

# ── Module-level model caches (loaded once, reused across queries) ──
_bge_model = None
_reranker = None


def _get_bge_model():
    global _bge_model
    if _bge_model is None:
        from FlagEmbedding import BGEM3FlagModel
        logger.info("Loading BGE-M3 model (first call — caching)...")
        _bge_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        logger.info("BGE-M3 model loaded")
    return _bge_model


def _get_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker
        logger.info("Loading BGE reranker (first call — caching)...")
        _reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
        logger.info("BGE reranker loaded")
    return _reranker


def hybrid_search(query: str, top_k: int = 8) -> dict:
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


def quick_search(query: str, top_k: int = 5) -> dict:
    """Lightweight search — vector only, no BM25, no reranking. For chat speed."""
    vector_results = _vector_search(query, top_k)
    graph_results = _graph_search(query, top_k)
    all_results = vector_results + graph_results
    all_results.sort(key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)

    return {
        "query": query,
        "results": all_results[:top_k],
        "source_breakdown": {
            "bm25": 0,
            "vector": len(vector_results),
            "graph": len(graph_results),
        },
        "searched_at": datetime.now(timezone.utc).isoformat(),
    }


# ── BM25 ──

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


# ── Merge & Rerank ──

def _merge_and_rerank(query: str, results: list[dict], top_k: int) -> list[dict]:
    # 1. Deduplicate by document_id, keeping highest-scoring instance
    seen_ids = set()
    deduplicated = []
    for r in sorted(results, key=lambda x: x.get("score", 0), reverse=True):
        doc_id = r.get("document_id")
        if doc_id and doc_id not in seen_ids:
            seen_ids.add(doc_id)
            deduplicated.append(r)

    if not deduplicated:
        return []

    # 2. Reciprocal Rank Fusion across the three source types
    k = 60
    fused = {}
    for i, r in enumerate(deduplicated):
        rank = i + 1
        fused[r["document_id"]] = fused.get(r["document_id"], 0) + 1.0 / (k + rank)
    for r in deduplicated:
        r["fused_score"] = fused.get(r["document_id"], r.get("score", 0))

    # 3. BGE Reranker-v2-m3 cross-encoder on top candidates
    try:
        reranker = _get_reranker()
        candidates = deduplicated[:max(top_k * 3, 20)]
        pairs = [[query, r.get("snippet", "")[:500]] for r in candidates]
        scores = reranker.compute_score(pairs, normalize=True)
        if isinstance(scores, float):
            scores = [scores]
        for i, r in enumerate(candidates[:len(scores)]):
            r["rerank_score"] = float(scores[i]) if scores[i] is not None else r.get("fused_score", 0)
    except Exception as e:
        logger.info(f"BGE reranker unavailable, using fused scores: {e}")
        for r in deduplicated:
            r["rerank_score"] = r.get("fused_score", r.get("score", 0))

    deduplicated.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    return deduplicated[:top_k]


# ── Vector Search (BGE-M3 → Qdrant) ──

def _vector_search(query: str, top_k: int) -> list[dict]:
    try:
        from qdrant_client import QdrantClient

        model = _get_bge_model()
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=5)

        query_embedding = model.encode([query], batch_size=1)
        query_vec = query_embedding["dense_vecs"][0].tolist()

        hits = qdrant.query_points(
            collection_name="planetmind_chunks",
            query=query_vec,
            limit=top_k,
        ).points

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


# ── Graph Search (Neo4j) ──

def _graph_search(query: str, top_k: int) -> list[dict]:
    try:
        import asyncio
        import concurrent.futures
        from backend.graphiti.retriever import graphiti_search

        def _run_in_thread():
            return asyncio.run(graphiti_search(query, top_k))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run_in_thread)
            return future.result(timeout=15)
    except Exception as e:
        logger.info(f"Graph search unavailable: {e}")
        return []

from datetime import datetime, timezone
from pathlib import Path
import json
from backend.config import settings
from backend.logging_config import logger


def hybrid_search(query: str, top_k: int = 10) -> dict:
    bm25_results = _bm25_search(query, top_k)

    merged = _merge_and_rerank(query, bm25_results, top_k)

    return {
        "query": query,
        "results": merged,
        "source_breakdown": {
            "bm25": len(bm25_results),
            "vector": 0,
            "graph": 0,
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
        if r["document_id"] not in seen_ids:
            seen_ids.add(r["document_id"])
            r["rerank_score"] = r["score"]
            deduplicated.append(r)
    return deduplicated[:top_k]

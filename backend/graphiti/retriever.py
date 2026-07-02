"""Graphiti query wrappers for hybrid_search and graph_api integration."""

from backend.graphiti.service import get_graphiti
from backend.logging_config import logger


async def graphiti_search(query: str, top_k: int = 8) -> list[dict]:
    """Search Graphiti knowledge graph. Returns provenance-linked results.

    Used by hybrid_search._graph_search() as a drop-in replacement for
    the legacy graph_searcher.search_graph().

    Returns:
        List of dicts with source, document_id, filename, score, snippet.
    """
    try:
        svc = get_graphiti()
        if not svc.is_available:
            await svc.initialize()
        return await svc.search(query, top_k)
    except Exception as e:
        logger.info(f"Graphiti search unavailable: {e}")
        return []


async def graphiti_graph_query(doc_filter: str | None = None) -> dict:
    """Build full graph data in vis-network-compatible format.

    Used by graph_api routes as a drop-in replacement for _build_graph_data().

    Returns:
        dict with nodes list and edges list.
    """
    try:
        svc = get_graphiti()
        if not svc.is_available:
            await svc.initialize()
        return await svc.get_full_graph(doc_filter)
    except Exception as e:
        logger.warning(f"Graphiti graph query failed: {e}")
        return {"nodes": [], "edges": [], "warning": "Graph data unavailable"}

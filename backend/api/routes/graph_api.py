"""Knowledge graph API — powered by Graphiti + Neo4j.

Replaces the legacy JSON-file-based entity scanning with Graphiti's native graph queries.
Maintains the exact same response format for downstream consumers (frontend vis-network).
"""

from fastapi import APIRouter
from backend.graphiti.retriever import graphiti_graph_query
from backend.logging_config import logger

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
async def graph_overview():
    """Return all graph nodes and relationships from Graphiti knowledge graph."""
    try:
        data = await graphiti_graph_query()
        logger.info(f"Graph overview: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
        if not data.get("nodes"):
            data["warning"] = "No graph data available — try uploading and processing documents first"
        return data
    except Exception as e:
        logger.warning(f"Graph overview failed: {e}")
        return {"nodes": [], "edges": [], "warning": "Graph data unavailable"}


@router.get("/{doc_id}")
async def get_document_graph(doc_id: str):
    """Return graph data filtered for a single document by episode source."""
    try:
        data = await graphiti_graph_query(doc_filter=doc_id)
        logger.info(f"Document graph {doc_id}: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
        return {**data, "document_id": doc_id}
    except Exception as e:
        logger.warning(f"Document graph failed for {doc_id}: {e}")
        return {"nodes": [], "edges": [], "document_id": doc_id, "warning": "Graph data unavailable"}

"""Graphiti temporal knowledge graph integration for PlanetMind.

Replaces the legacy JSON-file-based entity extraction and graph search with
Graphiti backed by Neo4j for temporal knowledge graph and memory.

Exports:
    GraphitiService — singleton service for ingestion, querying, health
    get_graphiti — module-level accessor
    graphiti_search — async search wrapper for hybrid_search integration
    graphiti_graph_query — async graph data builder for graph_api integration
    migrate_legacy_entities — one-shot migration from entities.json
"""
from backend.graphiti.service import GraphitiService, get_graphiti
from backend.graphiti.retriever import graphiti_search, graphiti_graph_query
from backend.graphiti.migrations import migrate_legacy_entities

__all__ = [
    "GraphitiService",
    "get_graphiti",
    "graphiti_search",
    "graphiti_graph_query",
    "migrate_legacy_entities",
]

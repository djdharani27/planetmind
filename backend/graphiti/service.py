"""GraphitiService — singleton wrapping Graphiti for ingestion, querying, and health.

Lazy initialization: connects to Neo4j on first use, not at import time.
Gracefully degrades when Neo4j/Graphiti are unavailable.
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from backend.config import settings
from backend.logging_config import logger


class GraphitiService:
    """Singleton service wrapping Graphiti for Neo4j-backed temporal knowledge graph.

    Usage:
        svc = get_graphiti()
        await svc.initialize()
        result = await svc.ingest_document_episode(...)
        results = await svc.search("query")
    """

    _instance: GraphitiService | None = None

    def __init__(self):
        self._client = None
        self._initialized = False
        self._init_error: str | None = None

    @classmethod
    def get_instance(cls) -> GraphitiService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_available(self) -> bool:
        return self._initialized and self._client is not None

    async def initialize(self) -> bool:
        """Connect to Neo4j and build Graphiti indices/constraints. Idempotent."""
        if self._initialized:
            return True

        try:
            from graphiti_core import Graphiti

            self._client = Graphiti(
                settings.neo4j_uri,
                settings.neo4j_user,
                settings.neo4j_password,
            )
            await self._client.build_indices_and_constraints()
            self._initialized = True
            self._init_error = None
            logger.info("GraphitiService initialized — Neo4j connected, indices built")
            return True
        except ImportError:
            self._init_error = "graphiti-core not installed"
            logger.warning(f"GraphitiService unavailable: {self._init_error}")
            return False
        except Exception as e:
            self._init_error = str(e)
            logger.warning(f"GraphitiService initialization failed: {e}")
            return False

    async def health_check(self) -> dict:
        """Health check returning node/edge/episode counts."""
        if not self.is_available:
            return {
                "healthy": False,
                "error": self._init_error or "not initialized",
                "node_count": 0,
                "edge_count": 0,
                "episode_count": 0,
            }
        try:
            driver = self._client.driver
            async with driver.session() as session:
                nodes = await session.run("MATCH (n:Entity) RETURN count(n) AS cnt")
                node_count = (await nodes.single())["cnt"]
                edges = await session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) AS cnt")
                edge_count = (await edges.single())["cnt"]
                episodes = await session.run("MATCH (e:Episodic) RETURN count(e) AS cnt")
                episode_count = (await episodes.single())["cnt"]
            return {
                "healthy": True,
                "node_count": node_count,
                "edge_count": edge_count,
                "episode_count": episode_count,
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "node_count": 0, "edge_count": 0, "episode_count": 0}

    async def ingest_document_episode(
        self,
        doc_id: str,
        filename: str,
        text: str,
        chunks: list[dict] | None = None,
    ) -> dict:
        """Ingest a document as a Graphiti Episode. Auto-extracts entities and relationships.

        Returns:
            dict with episode_uuid, entity_count, relationship_count on success.
        """
        if not self.is_available:
            return {"error": "Graphiti not available", "episode_uuid": "", "entity_count": 0, "relationship_count": 0}

        try:
            from graphiti_core.nodes import EpisodeType

            episode_name = f"doc:{doc_id}:{filename}"
            episode_body = text
            source = EpisodeType.text
            source_description = f"Document: {filename} (id: {doc_id})"

            result = await self._client.add_episode(
                name=episode_name,
                episode_body=episode_body,
                source=source,
                source_description=source_description,
                reference_time=datetime.now(timezone.utc),
            )

            logger.info(f"Graphiti episode ingested: {doc_id} — {filename}")
            return {
                "episode_uuid": str(result.uuid) if hasattr(result, "uuid") else episode_name,
                "entity_count": getattr(result, "entity_count", 0),
                "relationship_count": getattr(result, "relationship_count", 0),
            }
        except Exception as e:
            logger.error(f"Graphiti document ingestion failed for {doc_id}: {e}")
            return {"error": str(e), "episode_uuid": "", "entity_count": 0, "relationship_count": 0}

    async def ingest_conversation_episode(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str = "",
    ) -> dict:
        """Ingest a chat conversation turn as a Graphiti Episode."""
        if not self.is_available:
            return {"error": "Graphiti not available", "episode_uuid": ""}

        try:
            from graphiti_core.nodes import EpisodeType

            content = f"User: {user_message}"
            if assistant_response:
                content += f"\nAssistant: {assistant_response}"

            episode_name = f"conv:{session_id}:{datetime.now(timezone.utc).isoformat()}"
            source = EpisodeType.message
            source_description = f"Chat session: {session_id}"

            result = await self._client.add_episode(
                name=episode_name,
                episode_body=content,
                source=source,
                source_description=source_description,
                reference_time=datetime.now(timezone.utc),
            )

            logger.info(f"Graphiti conversation episode ingested for session {session_id}")
            return {"episode_uuid": str(result.uuid) if hasattr(result, "uuid") else episode_name}
        except Exception as e:
            logger.warning(f"Graphiti conversation ingestion failed: {e}")
            return {"error": str(e), "episode_uuid": ""}

    async def search(self, query: str, top_k: int = 8) -> list[dict]:
        """Run Graphiti hybrid edge search. Returns provenance-linked results."""
        if not self.is_available:
            return []

        try:
            results = await self._client.search(
                query,
                config={"limit": top_k},
            )

            items = []
            for r in results:
                items.append({
                    "source": "graph",
                    "document_id": getattr(r, "uuid", ""),
                    "filename": getattr(r, "name", "graph_entity"),
                    "score": getattr(r, "score", 0.0),
                    "snippet": getattr(r, "fact", "")[:300],
                    "fact": getattr(r, "fact", ""),
                    "valid_at": getattr(r, "valid_at", None),
                    "invalid_at": getattr(r, "invalid_at", None),
                })
            return items
        except Exception as e:
            logger.warning(f"Graphiti search failed: {e}")
            return []

    async def get_full_graph(self, doc_filter: str | None = None) -> dict:
        """Build nodes and edges in the format expected by the frontend vis-network.

        Compatible with the existing graph API contract:
            {nodes: [{id, label, group, type, context, confidence}],
             edges: [{from, to, label}]}
        """
        if not self.is_available:
            return {"nodes": [], "edges": [], "warning": "Graphiti unavailable"}

        try:
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

            # Get all entity nodes using node search
            node_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
            node_config.limit = 5000

            node_results = await self._client._search(
                query="*",
                config=node_config,
            )

            from backend.graphiti.models import ENTITY_TYPE_GROUPS

            nodes = []
            node_ids = set()
            edges = []
            edge_set = set()

            for node in node_results.nodes:
                nid = str(node.uuid)
                if nid in node_ids:
                    continue
                node_ids.add(nid)

                name = node.name or "Unnamed"
                labels = node.labels or ["Entity"]
                first_label = labels[0].lower() if labels else "entity"
                group = ENTITY_TYPE_GROUPS.get(first_label, first_label)
                node_type = first_label.title()

                context = node.summary[:200] if node.summary else ""

                nodes.append({
                    "id": nid,
                    "label": name[:35],
                    "group": group,
                    "type": node_type,
                    "context": context,
                    "confidence": 0.9,
                })

            # Get relationships via edge search
            edge_results = await self._client.search(
                "*",
                config={"limit": 10000},
            )

            for edge in edge_results:
                source = str(getattr(edge, "source_node_uuid", ""))
                target = str(getattr(edge, "target_node_uuid", ""))
                fact = getattr(edge, "fact", "") or "RELATES_TO"
                edge_key = f"{source}|{target}|{fact[:50]}"

                if edge_key not in edge_set and source and target:
                    edge_set.add(edge_key)
                    edges.append({
                        "from": source,
                        "to": target,
                        "label": fact[:30] if fact else "RELATES_TO",
                    })

            return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.warning(f"Graphiti full graph query failed: {e}")
            return {"nodes": [], "edges": [], "warning": str(e)}

    async def close(self):
        """Close the Graphiti client connection."""
        if self._client is not None:
            try:
                await self._client.close()
                self._initialized = False
                self._client = None
                logger.info("GraphitiService closed")
            except Exception as e:
                logger.warning(f"GraphitiService close error: {e}")


_graphiti_service: GraphitiService | None = None


def get_graphiti() -> GraphitiService:
    """Get or create the GraphitiService singleton."""
    global _graphiti_service
    if _graphiti_service is None:
        _graphiti_service = GraphitiService()
    return _graphiti_service

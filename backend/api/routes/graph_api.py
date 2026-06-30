from fastapi import APIRouter, HTTPException
from backend.logging_config import logger

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/{doc_id}")
async def get_document_graph(doc_id: str):
    """Return Neo4j nodes and relationships for a document."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        with driver.session() as session:
            result = session.run(
                """MATCH (d:Document {id: $doc_id})-[r:MENTIONS]->(n)
                   OPTIONAL MATCH (n)-[rel]-(related)
                   WHERE related:Document OR related:Equipment OR related:Failure OR related:Technician OR related:MaintenanceActivity OR related:Regulation
                   RETURN n, r, related, type(rel) as rel_type, labels(n) as node_labels, labels(related) as related_labels""",
                doc_id=doc_id,
            )
            records = list(result)
        driver.close()

        nodes = {}
        edges = []

        for rec in records:
            entity = rec["n"]
            node_labels = rec["node_labels"]
            entity_type = node_labels[0] if node_labels else "Unknown"

            nid = f"{entity_type}_{entity['value']}"
            if nid not in nodes:
                nodes[nid] = {
                    "id": nid,
                    "label": entity["value"],
                    "group": entity_type.lower(),
                    "type": entity_type,
                }

            edges.append({"from": f"Document_{doc_id}", "to": nid, "label": "MENTIONS"})

            if rec["related"]:
                rel_node = rec["related"]
                rlabels = rec["related_labels"]
                rtype = rlabels[0] if rlabels else "Unknown"
                rid = f"{rtype}_{rel_node['value']}"
                if rid not in nodes:
                    nodes[rid] = {
                        "id": rid,
                        "label": rel_node["value"],
                        "group": rtype.lower(),
                        "type": rtype,
                    }
                rel_type = rec["rel_type"] or "RELATED_TO"
                edges.append({"from": nid, "to": rid, "label": rel_type})

        nodes[f"Document_{doc_id}"] = {
            "id": f"Document_{doc_id}",
            "label": doc_id[:8],
            "group": "document",
            "type": "Document",
        }

        return {"nodes": list(nodes.values()), "edges": edges, "document_id": doc_id}
    except Exception as e:
        logger.warning(f"Graph query failed (Neo4j may not be running): {e}")
        return {"nodes": [], "edges": [], "document_id": doc_id, "warning": "Neo4j unavailable — graph data requires Neo4j service"}


@router.get("")
async def graph_overview():
    """Return all graph nodes and relationships."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        with driver.session() as session:
            result = session.run(
                """MATCH (n)-[r]->(m)
                   WHERE NOT n:Document AND NOT m:Document
                   OPTIONAL MATCH (d:Document)-[:MENTIONS]->(n)
                   RETURN labels(n) as from_labels, n.value as from_val,
                          labels(m) as to_labels, m.value as to_val,
                          type(r) as rel_type, collect(d.id) as documents
                   LIMIT 100"""
            )
            records = list(result)
        driver.close()

        nodes = {}
        edges = []
        for i, rec in enumerate(records):
            fl = rec["from_labels"][0] if rec["from_labels"] else "Unknown"
            tl = rec["to_labels"][0] if rec["to_labels"] else "Unknown"
            fv = rec["from_val"]
            tv = rec["to_val"]

            fid = f"{fl}_{fv}"
            tid = f"{tl}_{tv}"
            if fid not in nodes:
                nodes[fid] = {"id": fid, "label": fv, "group": fl.lower(), "type": fl}
            if tid not in nodes:
                nodes[tid] = {"id": tid, "label": tv, "group": tl.lower(), "type": tl}

            edges.append({
                "id": f"e{i}",
                "from": fid,
                "to": tid,
                "label": rec["rel_type"],
                "documents": rec["documents"],
            })

        return {"nodes": list(nodes.values()), "edges": edges}
    except Exception as e:
        logger.warning(f"Graph overview failed: {e}")
        return {"nodes": [], "edges": [], "warning": "Neo4j unavailable"}

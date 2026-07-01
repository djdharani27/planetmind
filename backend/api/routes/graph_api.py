import json
from pathlib import Path
from collections import defaultdict
from fastapi import APIRouter
from backend.config import settings
from backend.database.database import get_connection
from backend.logging_config import logger

router = APIRouter(prefix="/api/graph", tags=["graph"])

# Entity types that become Neo4j-style labels for grouping
ENTITY_TYPE_GROUPS = {
    "equipment":           "equipment",
    "component":           "component",
    "failure":             "failure",
    "maintenance_activity": "maintenanceactivity",
    "technician":          "technician",
    "regulation":          "regulation",
    "document":            "document",
    "location":            "location",
    "process_parameter":   "processparameter",
    "date":                "date",
}

RELATIONSHIP_RULES = [
    ("equipment", "failure",          "HAS_FAILURE"),
    ("equipment", "location",         "LOCATED_AT"),
    ("failure",   "technician",       "FIXED_BY"),
    ("equipment", "component",        "HAS_COMPONENT"),
    ("equipment", "process_parameter", "HAS_PARAMETER"),
    ("failure",   "maintenance_activity", "REQUIRES"),
    ("component", "failure",          "CAUSES"),
]


def _load_all_entities() -> list[dict]:
    """Read all processed entity files and attach their doc_id."""
    proc_dir: Path = settings.processed_dir
    if not proc_dir.exists():
        return []

    docs = {}
    conn = get_connection()
    rows = conn.execute("SELECT id, filename FROM documents").fetchall()
    conn.close()
    for r in rows:
        docs[r["id"]] = r["filename"]

    results = []
    for child in sorted(proc_dir.iterdir()):
        if not child.is_dir():
            continue
        ep = child / "entities.json"
        if not ep.exists():
            continue
        doc_id = child.name
        filename = docs.get(doc_id, doc_id[:8])
        try:
            entities = json.loads(ep.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(entities, list):
            continue
        results.append({"doc_id": doc_id, "filename": filename, "entities": entities})
    return results


def _build_graph_data(doc_filter: str | None = None) -> dict:
    """Build nodes and edges from entity JSON files.

    If *doc_filter* is set, only include entities from that document.
    """
    docs_data = _load_all_entities()
    if doc_filter:
        docs_data = [d for d in docs_data if d["doc_id"] == doc_filter]

    nodes_map: dict[str, dict] = {}
    edges: list[dict] = []
    edge_set: set[str] = set()
    doc_entity_map: dict[str, list[str]] = defaultdict(list)  # doc_id → [entity IDs]

    for dd in docs_data:
        doc_id = dd["doc_id"]
        doc_nid = f"Document_{doc_id}"

        # Document node
        if doc_nid not in nodes_map:
            nodes_map[doc_nid] = {
                "id": doc_nid,
                "label": dd["filename"],
                "group": "document",
                "type": "Document",
            }

        entities = dd["entities"]
        seen_in_doc: set[str] = set()

        for ent in entities:
            etype = (ent.get("type") or "").strip().lower()
            evalue = (ent.get("value") or "").strip()
            if not etype or not evalue or len(evalue) < 2:
                continue

            group = ENTITY_TYPE_GROUPS.get(etype, etype)
            enid = f"{group}_{evalue}"

            ctx = ent.get("context", "").strip()
            conf = ent.get("confidence")

            if enid not in nodes_map:
                nodes_map[enid] = {
                    "id": enid,
                    "label": evalue,
                    "group": group,
                    "type": etype.title(),
                    "context": ctx,
                    "confidence": conf,
                }
            else:
                # Merge context if this doc has a different one
                existing_ctx = nodes_map[enid].get("context", "")
                if ctx and ctx != existing_ctx:
                    nodes_map[enid]["context"] = existing_ctx + " | " + ctx if existing_ctx else ctx

            if enid not in seen_in_doc:
                seen_in_doc.add(enid)
                doc_entity_map[doc_id].append(enid)

                # Document → Entity edge
                ek = f"{doc_nid}|{enid}|CONTAINS"
                if ek not in edge_set:
                    edge_set.add(ek)
                    edges.append({
                        "from": doc_nid,
                        "to": enid,
                        "label": "CONTAINS",
                    })

        # Cross-entity relationships within this document
        typed: dict[str, list[str]] = defaultdict(list)
        for enid in seen_in_doc:
            # Infer type from the prefix part of the id
            for g in ENTITY_TYPE_GROUPS.values():
                if enid.startswith(f"{g}_"):
                    typed[g].append(enid)
                    break
            else:
                typed["unknown"].append(enid)

        for src_type, dst_type, rel_label in RELATIONSHIP_RULES:
            for src in typed.get(src_type, []):
                for dst in typed.get(dst_type, []):
                    if src == dst:
                        continue
                    # Prefer linking from equipment-specific to its related entities
                    ek = f"{src}|{dst}|{rel_label}"
                    if ek not in edge_set:
                        edge_set.add(ek)
                        edges.append({
                            "from": src,
                            "to": dst,
                            "label": rel_label,
                        })

    return {"nodes": list(nodes_map.values()), "edges": edges}


@router.get("")
async def graph_overview():
    """Return all graph nodes and relationships from processed entities."""
    try:
        data = _build_graph_data()
        logger.info(f"Graph overview: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
        return data
    except Exception as e:
        logger.warning(f"Graph overview failed: {e}")
        return {"nodes": [], "edges": [], "warning": "No graph data available"}


@router.get("/{doc_id}")
async def get_document_graph(doc_id: str):
    """Return graph for a single document."""
    try:
        data = _build_graph_data(doc_filter=doc_id)
        logger.info(f"Document graph {doc_id}: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
        return {**data, "document_id": doc_id}
    except Exception as e:
        logger.warning(f"Document graph failed for {doc_id}: {e}")
        return {"nodes": [], "edges": [], "document_id": doc_id, "warning": "No graph data available"}

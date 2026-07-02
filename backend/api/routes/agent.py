"""
Unified Agent Router — Kumar

Intelligent query dispatcher that routes natural language questions to the correct
backend agent: chat, search, maintenance, compliance, lessons, or knowledge graph.
"""

import json
import random
import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.search.hybrid_search import hybrid_search
from backend.llm.chat_assistant import generate_answer
from backend.llm.maintenance_rca import analyze_maintenance
from backend.llm.compliance_intel import analyze_compliance
from backend.llm.lessons_engine import analyze_lessons
from backend.api.routes.graph_api import graph_overview, get_document_graph
from backend.api import document_service as doc_svc
from backend.ingestion.pipeline import process_document
from backend.logging_config import logger

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRequest(BaseModel):
    query: str
    top_k: int = 15
    mode: str = "auto"  # auto | chat | search | maintenance | compliance | lessons | graph
    session_id: str = ""  # conversation session identifier (auto-generated if empty)


def detect_intent(query: str) -> str:
    q = query.lower().strip()

    # Casual greetings & small talk — respond naturally, no search needed
    greeting_words = {"hi", "hello", "hey", "hai", "howdy", "sup", "yo", "namaste", "kumar"}
    greeting_phrases = {
        "good morning", "good afternoon", "good evening", "what's up", "wassup",
        "how are you", "how are you doing", "how's it going", "nice to meet you",
        "hey there", "hey hai", "hi there", "hello there", "hey hey",
    }
    q_clean = q.rstrip("?!.,;:")
    if not q_clean:
        return "chat"
    words = q_clean.split()
    if q_clean in greeting_phrases or (words and words[0] in greeting_words and len(words) <= 3):
        return "greeting"
    # Single-word non-keyword queries (names, casual mentions) → greeting
    if len(words) == 1 and not any(kw in q for kw in [
        "root cause", "rca", "failure", "fail", "breakdown", "repair", "fix",
        "maintenance", "predictive", "schedule", "inspection", "bearing",
        "lubrication", "vibration", "overheat", "fatigue", "corrosion",
        "worn", "crack", "misalignment", "wear", "compliance", "regulation",
        "regulatory", "audit", "iso", "lesson", "incident", "near miss",
        "warning", "risk", "learned", "accident", "graph", "knowledge graph",
        "process", "pipeline", "embedding", "find", "search", "look up",
    ]):
        return "greeting"

    # Maintenance / RCA
    if any(kw in q for kw in [
        "root cause", "rca", "failure", "fail", "breakdown", "repair", "fix",
        "maintenance", "predictive", "schedule", "inspection", "bearing",
        "lubrication", "vibration", "overheat", "fatigue", "corrosion",
        "worn", "crack", "misalignment", "wear"
    ]):
        return "maintenance"

    # Compliance / Regulatory
    if any(kw in q for kw in [
        "compliance", "regulation", "regulatory", "audit", "iso", "factory act",
        "oisd", "peso", "legal", "gap analysis", "corrective action",
        "quality", "standard", "certification", "environmental"
    ]):
        return "compliance"

    # Lessons / Incidents
    if any(kw in q for kw in [
        "lesson", "incident", "near miss", "warning", "risk", "learned",
        "accident", "pattern", "systemic", "proactive", "occurrence"
    ]):
        return "lessons"

    # Knowledge graph
    if any(kw in q for kw in [
        "graph", "knowledge graph", "relationship", "entity", "show me everything",
        "full graph", "network", "how things connect", "all entities",
        "show graph", "visualize", "connections between"
    ]):
        return "graph"

    # Process / Pipeline
    if any(kw in q for kw in [
        "process", "pipeline", "embedding", "pending", "reprocess",
        "unprocessed", "processing status", "process documents",
        "process all", "generate embedding", "build graph"
    ]):
        return "process"

    # Search — explicit lookups
    if any(kw in q for kw in [
        "find", "search", "look up", "document about", "show me documents",
        "where is", "what document"
    ]):
        return "search"

    # Default to general chat
    return "chat"


def _summarize_maintenance(raw: dict) -> str:
    lines = []
    if raw.get("root_causes"):
        lines.append("**Root Causes Identified:**")
        for rc in raw["root_causes"][:3]:
            lines.append(f"- {rc['cause']} (confidence: {rc.get('confidence', 0)*100:.0f}%)")
    if raw.get("predictive_recommendations"):
        lines.append("\n**Recommended Actions:**")
        for pr in raw["predictive_recommendations"][:3]:
            lines.append(f"- {pr['action']} (every {pr.get('interval_days', 'N/A')} days)")
    if raw.get("failure_patterns"):
        lines.append("\n**Failure Patterns:**")
        for fp in raw["failure_patterns"][:3]:
            lines.append(f"- {fp.get('pattern', '')[:120]}")
    conf = raw.get("overall_confidence", 0)
    lines.append(f"\n*Overall Confidence: {conf*100:.0f}%*")
    return "\n".join(lines) if lines else "No structured maintenance data returned."


def _summarize_compliance(raw: dict) -> str:
    lines = []
    if raw.get("applicable_regulations"):
        lines.append("**Applicable Regulations:** " + ", ".join(raw["applicable_regulations"]))
    if raw.get("compliance_gaps"):
        lines.append("\n**Compliance Gaps:**")
        for g in raw["compliance_gaps"][:5]:
            sv = g.get("severity", "unknown")
            badge = "🔴" if sv == "critical" else "🟠" if sv == "high" else "🟡"
            lines.append(f"- {badge} {g.get('requirement', '')}: {g.get('gap', '')}")
    if raw.get("corrective_actions"):
        lines.append("\n**Corrective Actions:**")
        for ca in raw["corrective_actions"][:3]:
            lines.append(f"- {ca['action']} (priority {ca.get('priority', 'N/A')}, due {ca.get('deadline_days', 'N/A')}d)")
    score = raw.get("overall_compliance_score", 0)
    lines.append(f"\n*Overall Compliance Score: {score*100:.0f}%*")
    return "\n".join(lines) if lines else "No structured compliance data returned."


def _summarize_lessons(raw: dict) -> str:
    lines = []
    if raw.get("identified_patterns"):
        lines.append("**Identified Patterns:**")
        for p in raw["identified_patterns"][:3]:
            lines.append(f"- {p.get('pattern', '')} ({p.get('occurrences', 0)} occurrences)")
    if raw.get("proactive_warnings"):
        lines.append("\n**Proactive Warnings:**")
        for w in raw["proactive_warnings"][:3]:
            urg = w.get("urgency", "informational")
            badge = "🔴" if urg == "immediate" else "🟠" if urg == "soon" else "ℹ️"
            lines.append(f"- {badge} {w['warning']} (→ {w.get('target_team', 'All')})")
    if raw.get("systemic_risks"):
        lines.append("\n**Systemic Risks:**")
        for sr in raw["systemic_risks"][:3]:
            pct = {"high": 70, "medium": 50, "low": 30}.get(sr.get("probability", "medium"), 50)
            ict = {"critical": 90, "high": 70, "medium": 50, "low": 30}.get(sr.get("impact", "medium"), 50)
            lines.append(f"- {sr['risk']} (probability: {pct}%, impact: {ict}%)")
    if raw.get("lessons_learned"):
        lines.append("\n**Lessons Learned:**")
        for ll in raw["lessons_learned"][:3]:
            eq = ", ".join(ll.get("applicable_equipment", []))
            lines.append(f"- {ll['lesson']}" + (f" — applies to: {eq}" if eq else ""))
    score = raw.get("overall_risk_score", 0)
    lines.append(f"\n*Overall Risk Score: {score*100:.0f}%*")
    return "\n".join(lines) if lines else "No structured lessons data returned."


@router.post("/query")
async def agent_query(request: AgentRequest):
    query = request.query
    mode = request.mode

    # 1. Detect intent
    intent = detect_intent(query) if mode == "auto" else mode
    tools_used = [intent]
    logger.info(f"Agent query — intent={intent}, query={query[:80]}")

    try:
        # 2. Route to the right tool
        if intent == "greeting":
            greetings = [
                "Hello! I'm Kumar. Got questions about your equipment, maintenance history, or compliance status? I've been in this industry long enough — ask me anything.",
                "Hey there, Kumar here. What can I dig into for you? Failures, documents, compliance — just point me where to look.",
                "Kumar here. I've got your documents loaded and ready. What do you need to know about your operations today?",
                "You've got Kumar on the job. Tell me what you're looking for — I'll find it in the data.",
                "Welcome. I've been working industrial intelligence for decades. What's the question?",
            ]
            return {
                "answer": random.choice(greetings),
                "intent": "greeting",
                "tools_used": [],
                "sources": [],
                "confidence": 100,
                "answered_at": datetime.now(timezone.utc).isoformat(),
            }

        if intent == "graph":
            graph_data = await graph_overview()
            if graph_data.get("warning"):
                return {
                    "answer": "The knowledge graph is currently unavailable. Neo4j doesn't appear to be running — start it with `docker compose -f docker/docker-compose.yml up -d neo4j`.",
                    "intent": "graph",
                    "tools_used": tools_used,
                    "graph_data": {"nodes": [], "edges": []},
                    "sources": [],
                    "confidence": 0,
                    "answered_at": datetime.now(timezone.utc).isoformat(),
                }
            if not graph_data.get("nodes"):
                return {
                    "answer": "Your knowledge graph is empty — there are no entities yet. Upload and process documents to populate it with equipment, failures, components, and their relationships.",
                    "intent": "graph",
                    "tools_used": tools_used,
                    "graph_data": {"nodes": [], "edges": []},
                    "sources": [],
                    "confidence": 0,
                    "answered_at": datetime.now(timezone.utc).isoformat(),
                }
            return {
                "answer": f"Here's the full knowledge graph — **{len(graph_data['nodes'])} entities** and **{len(graph_data['edges'])} relationships** across your organization's data.",
                "intent": "graph",
                "tools_used": tools_used,
                "graph_data": graph_data,
                "sources": [],
                "confidence": 95,
                "answered_at": datetime.now(timezone.utc).isoformat(),
            }

        # Process / Pipeline — no search needed, works on document status
        if intent == "process":
            all_docs = doc_svc.list_documents()
            pending = [d for d in all_docs if d.get("processing_status") in ("uploaded", "failed")]
            processing = [d for d in all_docs if d.get("processing_status") == "processing"]
            completed = [d for d in all_docs if d.get("processing_status") == "completed"]

            lines = []
            total = len(all_docs)
            lines.append(f"### Document Processing Pipeline\n")
            lines.append(f"**Total documents:** {total}")
            lines.append(f"- ✅ **Completed:** {len(completed)}")
            lines.append(f"- ⏳ **Processing:** {len(processing)}")
            lines.append(f"- ⏸️ **Pending/Failed:** {len(pending)}")
            lines.append("")

            if pending:
                lines.append("**Pending documents (click to process):**")
                for d in pending[:10]:
                    fid = d.get("filename", "unknown")
                    pid = d["id"]
                    status_icon = "❌" if d.get("processing_status") == "failed" else "⏸️"
                    lines.append(f"- {status_icon} `{fid}` — `{pid[:8]}...`")
                lines.append("")

            if processing:
                lines.append("**Currently processing:**")
                for d in processing[:5]:
                    lines.append(f"- ⏳ `{d.get('filename', 'unknown')}`")

            answer = "\n".join(lines) if lines else "No documents found."
            return {
                "answer": answer,
                "intent": "process",
                "tools_used": tools_used,
                "structured_data": {
                    "total": total,
                    "completed": len(completed),
                    "processing": len(processing),
                    "pending": len(pending),
                    "documents": [
                        {"id": d["id"], "filename": d.get("filename", "unknown"),
                         "status": d.get("processing_status", "unknown"),
                         "type": d.get("file_type", ""), "size": d.get("file_size", 0)}
                        for d in all_docs[:50]
                    ],
                },
                "sources": [],
                "confidence": 100,
                "answered_at": datetime.now(timezone.utc).isoformat(),
            }

        # Search results needed for specialized intents (maintenance, compliance, lessons, search)
        # Chat intent uses the ReAct agent which handles search internally
        if intent != "chat":
            search_data = hybrid_search(query, top_k=request.top_k)
            search_results = search_data["results"]
        else:
            search_results = []

        if intent == "search":
            formatted = []
            for r in search_results[:8]:
                formatted.append(
                    f"**{r.get('filename', r.get('document_id', 'Unknown'))}**"
                    + (f" (p.{r['page_number']})" if r.get("page_number") else "")
                    + f"\n> {r.get('snippet', '')[:200]}..."
                    + f"\n*Score: {r.get('rerank_score', r.get('score', 0)):.2f}*"
                )
            answer = "### Search Results\n\n" + "\n\n".join(formatted) if formatted else "No relevant documents found."
            return {
                "answer": answer,
                "intent": "search",
                "tools_used": tools_used,
                "sources": [
                    {"document_id": r.get("document_id", ""), "filename": r.get("filename", ""),
                     "page": r.get("page_number", 1), "score": r.get("rerank_score", r.get("score", 0))}
                    for r in search_results[:5]
                ],
                "confidence": min(90, len(search_results) * 10 + 20) if search_results else 0,
                "answered_at": datetime.now(timezone.utc).isoformat(),
            }

        if intent == "maintenance":
            analysis = analyze_maintenance(query, request.top_k)
            if "error" in analysis:
                return {"answer": analysis["error"], "intent": "maintenance", "tools_used": tools_used,
                        "sources": [], "confidence": 0, "answered_at": datetime.now(timezone.utc).isoformat()}
            summary = _summarize_maintenance(analysis)
            return {
                "answer": f"### Maintenance Intelligence Report\n\n{summary}" + _sources_block(analysis.get("sources", [])),
                "intent": "maintenance",
                "tools_used": tools_used,
                "structured_data": analysis,
                "sources": analysis.get("sources", []),
                "confidence": analysis.get("overall_confidence", 0.5) * 100,
                "answered_at": analysis.get("analyzed_at", datetime.now(timezone.utc).isoformat()),
            }

        if intent == "compliance":
            analysis = analyze_compliance(query, request.top_k)
            if "error" in analysis:
                return {"answer": analysis["error"], "intent": "compliance", "tools_used": tools_used,
                        "sources": [], "confidence": 0, "answered_at": datetime.now(timezone.utc).isoformat()}
            summary = _summarize_compliance(analysis)
            return {
                "answer": f"### Compliance Intelligence Report\n\n{summary}" + _sources_block(analysis.get("sources", [])),
                "intent": "compliance",
                "tools_used": tools_used,
                "structured_data": analysis,
                "sources": analysis.get("sources", []),
                "confidence": analysis.get("overall_compliance_score", 0.5) * 100,
                "answered_at": analysis.get("analyzed_at", datetime.now(timezone.utc).isoformat()),
            }

        if intent == "lessons":
            analysis = analyze_lessons(query, request.top_k)
            if "error" in analysis:
                return {"answer": analysis["error"], "intent": "lessons", "tools_used": tools_used,
                        "sources": [], "confidence": 0, "answered_at": datetime.now(timezone.utc).isoformat()}
            summary = _summarize_lessons(analysis)
            return {
                "answer": f"### Lessons Learned Report\n\n{summary}" + _sources_block(analysis.get("sources", [])),
                "intent": "lessons",
                "tools_used": tools_used,
                "structured_data": analysis,
                "sources": analysis.get("sources", []),
                "confidence": max(30, 100 - analysis.get("overall_risk_score", 0.5) * 100),
                "answered_at": analysis.get("analyzed_at", datetime.now(timezone.utc).isoformat()),
            }

        # Default: general chat / Q&A
        # The ReAct agent handles search internally via tool calling
        answer = await generate_answer(query)
        answer_text = answer.get("answer", "I couldn't find an answer to that question.")

        # Fire-and-forget: ingest conversation turn into Graphiti memory
        sid = request.session_id or str(uuid.uuid4())
        asyncio.create_task(_ingest_chat_turn(sid, query, answer_text))

        return {
            "answer": answer_text,
            "intent": "chat",
            "tools_used": tools_used,
            "sources": answer.get("sources", []),
            "confidence": answer.get("confidence", 50),
            "related": answer.get("related", {}),
            "graph_data": answer.get("graph_data"),
            "session_id": sid,
            "answered_at": answer.get("answered_at", datetime.now(timezone.utc).isoformat()),
        }

    except Exception as e:
        logger.error(f"Agent query failed: {e}", exc_info=True)
        raise HTTPException(500, f"Agent processing failed: {str(e)}")


async def _ingest_chat_turn(session_id: str, query: str, answer: str):
    """Ingest a chat conversation turn into Graphiti as a temporal episode."""
    try:
        from backend.graphiti.service import get_graphiti
        graphiti = get_graphiti()
        if not graphiti.is_available:
            await graphiti.initialize()
        await graphiti.ingest_conversation_episode(
            session_id=session_id,
            user_message=query,
            assistant_response=answer,
        )
    except Exception as e:
        logger.warning(f"Chat ingestion skipped for session {session_id}: {e}")


def _sources_block(sources: list) -> str:
    if not sources:
        return ""
    lines = ["\n\n**Sources:**"]
    for s in sources[:4]:
        sid = s.get("document_id", "unknown")
        snippet = s.get("snippet", "")[:60]
        lines.append(f"- `{sid[:12]}...` {snippet}")
    return "\n".join(lines)


class ProcessActionRequest(BaseModel):
    document_id: str | None = None


@router.post("/process")
async def process_documents(request: ProcessActionRequest):
    """Trigger document processing — all pending if no document_id specified, or a specific document."""
    try:
        if request.document_id:
            doc = doc_svc.get_document(request.document_id)
            if not doc:
                raise HTTPException(404, f"Document {request.document_id} not found")
            result = process_document(request.document_id)
            return {
                "status": "completed",
                "document_id": request.document_id,
                "filename": doc.get("filename", "unknown"),
                "result": result,
            }

        all_docs = doc_svc.list_documents()
        pending = [d for d in all_docs if d.get("processing_status") in ("uploaded", "failed")]
        if not pending:
            return {"status": "no_pending", "message": "No pending documents to process.", "processed": 0}

        results = []
        for doc in pending[:10]:  # Process up to 10 at a time
            try:
                result = process_document(doc["id"])
                results.append({
                    "document_id": doc["id"],
                    "filename": doc.get("filename", "unknown"),
                    "status": "completed",
                })
            except Exception as e:
                results.append({
                    "document_id": doc["id"],
                    "filename": doc.get("filename", "unknown"),
                    "status": "failed",
                    "error": str(e),
                })

        return {
            "status": "batch_completed",
            "processed": len([r for r in results if r["status"] == "completed"]),
            "failed": len([r for r in results if r["status"] == "failed"]),
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process action failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))

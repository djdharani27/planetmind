"""
Unified Agent Router — Kumar

Intelligent query dispatcher that routes natural language questions to the correct
backend agent: chat, search, maintenance, compliance, lessons, or knowledge graph.
"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.search.hybrid_search import hybrid_search
from backend.llm.chat_assistant import generate_answer
from backend.llm.maintenance_rca import analyze_maintenance
from backend.llm.compliance_intel import analyze_compliance
from backend.llm.lessons_engine import analyze_lessons
from backend.api.routes.graph_api import graph_overview, get_document_graph
from backend.logging_config import logger

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRequest(BaseModel):
    query: str
    top_k: int = 15
    mode: str = "auto"  # auto | chat | search | maintenance | compliance | lessons | graph


def detect_intent(query: str) -> str:
    q = query.lower()

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
        if intent == "graph":
            graph_data = await graph_overview()
            if not graph_data.get("nodes"):
                return {
                    "answer": "The knowledge graph is currently unavailable. This usually means Neo4j isn't running. Try starting the Neo4j service first.",
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

        # Search, Chat, Maintenance, Compliance, Lessons — all need search results
        search_results = hybrid_search(query, request.top_k)["results"]

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
        answer = generate_answer(query, search_results)
        return {
            "answer": answer.get("answer", "I couldn't find an answer to that question."),
            "intent": "chat",
            "tools_used": tools_used,
            "sources": answer.get("sources", []),
            "confidence": answer.get("confidence", 50),
            "related": answer.get("related", {}),
            "answered_at": answer.get("answered_at", datetime.now(timezone.utc).isoformat()),
        }

    except Exception as e:
        logger.error(f"Agent query failed: {e}", exc_info=True)
        raise HTTPException(500, f"Agent processing failed: {str(e)}")


def _sources_block(sources: list) -> str:
    if not sources:
        return ""
    lines = ["\n\n**Sources:**"]
    for s in sources[:4]:
        sid = s.get("document_id", "unknown")
        snippet = s.get("snippet", "")[:60]
        lines.append(f"- `{sid[:12]}...` {snippet}")
    return "\n".join(lines)

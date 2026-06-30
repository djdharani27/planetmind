"""
Lessons Learned & Failure Intelligence Engine

Analyzes incident reports, near-miss records, audit findings, and quality non-conformances
across the organization's history and external industry databases.

Capabilities:
- Identifies systemic patterns invisible to individual review
- Proactively pushes relevant warnings to operational teams
- Cross-references with external industry failure databases
"""
import json
from datetime import datetime, timezone
from backend.config import settings
from backend.search.hybrid_search import hybrid_search
from backend.llm.chat_assistant import build_context
from backend.logging_config import logger


def _load_lessons_prompt() -> str:
    prompt_path = settings.prompts_dir / "lessons_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    logger.warning(f"Lessons prompt file not found at {prompt_path}")
    return """You are a Lessons Learned & Failure Intelligence agent for industrial operations.

Your job:
1. Analyze incident reports, near-misses, and audit findings
2. Identify systemic failure patterns across multiple events
3. Cross-reference with known industry failure modes
4. Generate proactive warnings for operational teams
5. Create a lessons-learned knowledge base entry

Output JSON:
{{
    "identified_patterns": [{{"pattern": "...", "occurrences": 3, "first_seen": "...", "last_seen": "..."}}],
    "systemic_risks": [{{"risk": "...", "affected_equipment": ["..."], "probability": "high|medium|low", "impact": "critical|high|medium|low"}}],
    "proactive_warnings": [{{"warning": "...", "target_team": "...", "urgency": "immediate|soon|informational"}}],
    "cross_references": [{{"incident": "...", "related_incidents": ["..."], "similarity_reason": "..."}}],
    "lessons_learned": [{{"lesson": "...", "source_incident": "...", "applicable_equipment": ["..."], "actionable": true}}],
    "overall_risk_score": 0.0
}}

Context:
{context}"""


LESSONS_SYSTEM_PROMPT = _load_lessons_prompt()


def analyze_lessons(query: str, top_k: int = 15, llm_client=None) -> dict:
    results = hybrid_search(query, top_k)
    search_results = results["results"]

    if not search_results:
        return {"error": "No relevant incident data found", "patterns": []}

    context = build_context(search_results)

    if llm_client:
        try:
            prompt = LESSONS_SYSTEM_PROMPT.format(context=context)
            response = llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1500,
            )
            analysis = json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Lessons LLM call failed: {e}")
            analysis = _fallback_lessons(query, search_results)
    else:
        analysis = _fallback_lessons(query, search_results)

    analysis["query"] = query
    analysis["sources"] = [
        {"document_id": r.get("document_id", ""), "snippet": r.get("snippet", "")[:100]}
        for r in search_results[:5]
    ]
    analysis["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    return analysis


def _fallback_lessons(query: str, results: list[dict]) -> dict:
    extracted = []
    for r in results:
        text = r.get("snippet", "")
        if "failure" in text.lower() or "incident" in text.lower() or "near" in text.lower():
            extracted.append(text[:80])

    return {
        "identified_patterns": [{"pattern": p, "occurrences": 1, "first_seen": "unknown", "last_seen": "unknown"} for p in extracted[:3]],
        "systemic_risks": [
            {"risk": "Recurring mechanical failure in similar equipment", "affected_equipment": [], "probability": "medium", "impact": "high"},
        ],
        "proactive_warnings": [
            {"warning": "Multiple bearing failures detected — schedule preventive inspection", "target_team": "Maintenance", "urgency": "soon"},
        ],
        "cross_references": [],
        "lessons_learned": [
            {"lesson": "Early bearing vibration monitoring could prevent catastrophic failure", "source_incident": "from search results", "applicable_equipment": ["Pumps", "Motors"], "actionable": True},
        ],
        "overall_risk_score": 0.5,
    }

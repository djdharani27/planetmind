"""
Quality & Regulatory Compliance Intelligence

Maps regulatory requirements (Factory Act, OISD, PESO, environmental norms, quality standards)
against current procedures, equipment states, and inspection records.

Capabilities:
- Identifies compliance gaps
- Auto-generates compliance evidence packages for audits
- Flags quality deviations before they escalate
"""
import json
from datetime import datetime, timezone
from backend.config import settings
from backend.search.hybrid_search import hybrid_search
from backend.llm.chat_assistant import build_context
from backend.logging_config import logger


def _load_compliance_prompt() -> str:
    prompt_path = settings.prompts_dir / "compliance_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    logger.warning(f"Compliance prompt file not found at {prompt_path}")
    return """You are a Quality & Regulatory Compliance Intelligence agent for industrial operations.

Applicable regulations: Factory Act, OISD, PESO, ISO 9001, ISO 14001, ISO 45001, environmental norms.

Your job:
1. Analyze documents against applicable regulatory requirements
2. Identify compliance gaps with severity ratings
3. Generate evidence packages for audit preparation
4. Flag quality deviations with risk assessment
5. Suggest corrective actions with priority

Output JSON:
{{
    "applicable_regulations": ["Factory Act", "OISD", "ISO 9001"],
    "compliance_gaps": [{{"requirement": "...", "gap": "...", "severity": "critical|high|medium|low", "risk": "..."}}],
    "evidence_package": [{{"document": "...", "clause": "...", "status": "compliant|partial|noncompliant"}}],
    "quality_deviations": [{{"deviation": "...", "impact": "...", "detected_in": "..."}}],
    "corrective_actions": [{{"action": "...", "priority": 1, "deadline_days": 30}}],
    "overall_compliance_score": 0.0
}}

Context:
{context}"""


COMPLIANCE_SYSTEM_PROMPT = _load_compliance_prompt()


def analyze_compliance(query: str, top_k: int = 15, llm_client=None) -> dict:
    results = hybrid_search(query, top_k)
    search_results = results["results"]

    if not search_results:
        return {"error": "No relevant compliance data found", "gaps": []}

    context = build_context(search_results)

    if llm_client:
        try:
            prompt = COMPLIANCE_SYSTEM_PROMPT.format(context=context)
            response = llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1500,
            )
            analysis = json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Compliance LLM call failed: {e}")
            analysis = _fallback_compliance(query, search_results)
    else:
        analysis = _fallback_compliance(query, search_results)

    analysis["query"] = query
    analysis["sources"] = [
        {"document_id": r.get("document_id", ""), "snippet": r.get("snippet", "")[:100]}
        for r in search_results[:5]
    ]
    analysis["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    return analysis


def _fallback_compliance(query: str, results: list[dict]) -> dict:
    regulations_found = []
    for r in results:
        text = r.get("snippet", "")
        for reg in ["Factory Act", "OISD", "PESO", "ISO"]:
            if reg.lower() in text.lower() and reg not in regulations_found:
                regulations_found.append(reg)

    return {
        "applicable_regulations": regulations_found or ["Factory Act", "OISD"],
        "compliance_gaps": [
            {"requirement": "Periodic inspection under Factory Act", "gap": "Last inspection date not found in records", "severity": "high", "risk": "Potential fine for non-compliance"},
        ],
        "evidence_package": [
            {"document": r.get("document_id", "unknown"), "clause": "Inspection clause", "status": "partial"}
            for r in results[:3]
        ],
        "quality_deviations": [],
        "corrective_actions": [
            {"action": "Schedule immediate Factory Act inspection", "priority": 1, "deadline_days": 14},
        ],
        "overall_compliance_score": 0.6,
    }

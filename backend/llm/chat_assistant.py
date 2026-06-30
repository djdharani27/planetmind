from datetime import datetime, timezone
from backend.config import settings
from backend.logging_config import logger


def _load_chat_prompt() -> str:
    prompt_path = settings.prompts_dir / "chat_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    logger.warning(f"Chat prompt file not found at {prompt_path}, using inline fallback")
    return """You are an industrial AI copilot for PlanetMind AI. You answer operational, maintenance,
and engineering questions using retrieved document context.

Rules:
1. Answer ONLY based on provided context. If uncertain, say so.
2. Include source citations with document name and page number.
3. Provide confidence score (0-100%) for your answer.
4. List related equipment, failures, and maintenance records when relevant.
5. Be concise but thorough — target field technicians and engineers.

Context:
{context}

Question: {question}"""


CHAT_SYSTEM_PROMPT = _load_chat_prompt()


def build_context(search_results: list[dict]) -> str:
    """Build context string from search results."""
    parts = []
    for i, r in enumerate(search_results):
        parts.append(
            f"[Source {i + 1}] "
            f"Document: {r.get('filename', r.get('document_id', 'unknown'))}, "
            f"Page: {r.get('page_number', 'N/A')}\n"
            f"Content: {r.get('snippet', '')}\n"
        )
    return "\n---\n".join(parts)


def generate_answer(question: str, search_results: list[dict], llm_client=None) -> dict:
    """Generate AI answer with sources, confidence, and related entities."""
    context = build_context(search_results)
    prompt = CHAT_SYSTEM_PROMPT.format(context=context, question=question)

    if llm_client:
        try:
            response = llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
            )
            answer_text = response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            answer_text = _fallback_answer(question, search_results)
    else:
        answer_text = _fallback_answer(question, search_results)

    sources = []
    seen = set()
    for r in search_results:
        doc_id = r.get("document_id", "")
        if doc_id not in seen:
            seen.add(doc_id)
            sources.append({
                "document_id": doc_id,
                "filename": r.get("filename", doc_id),
                "page": r.get("page_number", 1),
                "relevance_score": r.get("rerank_score", r.get("score", 0)),
            })

    confidence = min(95, max(30, len(seen) * 15 + 40)) if search_results else 10

    related = {}
    for r in search_results:
        if "entity" in r and "entity_type" in r:
            t = r["entity_type"]
            if t not in related:
                related[t] = []
            if r["entity"] not in related[t]:
                related[t].append(r["entity"])

    return {
        "question": question,
        "answer": answer_text,
        "confidence": confidence,
        "sources": sources[:5],
        "related": related,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }


def _fallback_answer(question: str, results: list[dict]) -> str:
    if not results:
        return "I couldn't find relevant information to answer this question. Please try rephrasing or check if the relevant documents have been uploaded."
    lines = ["Based on the available documents, here's what I found:\n"]
    for i, r in enumerate(results[:3]):
        lines.append(f"- {r.get('snippet', '')[:150]}...")
    return "\n".join(lines)

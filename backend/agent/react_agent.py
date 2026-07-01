"""ReAct agent — tool-calling loop using OpenAI function calling.

The agent decides when to use tools (search_documents) and when to
respond directly. Never falls back to raw snippet dumps.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from backend.config import settings
from backend.logging_config import logger
from backend.agent.tools import get_openai_tools, get_tool_by_name

SYSTEM_PROMPT = """You are Kumar — a veteran in industrial intelligence with decades of field experience.

You answer operational, maintenance, and engineering questions using retrieved document context.
You have access to tools that search the company's document repository.

**Your principles:**
1. TRUTH FIRST — Only give information supported by the documents. Never guess.
2. TOOL USE — Use the `search_documents` tool to find relevant information before answering.
3. CITATIONS — Always cite specific document names and page numbers when you use information from search results.
4. CONCISE — Field engineers need answers fast. Be direct and precise.
5. NO HALLUCINATION — If the search results don't contain the answer, say so clearly:
   "I don't have that information in the available documents."
6. RELEVANCE — Only include data that directly answers the question. No filler.
7. POLITE — You're a seasoned professional. Be respectful and helpful.

**How to respond:**
- For factual questions: Call `search_documents` first, then synthesize the results into a clear answer.
- The search tool returns document snippets with source info — use those to cite your sources.
- If you already know the information from search results, provide the answer directly with citations.
- If the search returns nothing relevant, say so — never fabricate."""


def _format_search_results(search_output) -> str:
    """Format search results into a readable string for the LLM."""
    if not search_output.results:
        return "No relevant documents found."

    parts = []
    for i, r in enumerate(search_output.results, 1):
        page = f" (page {r.page_number})" if r.page_number else ""
        parts.append(
            f"[Source {i}] Document: {r.filename}{page}\n"
            f"Content: {r.snippet}\n"
        )
    return "\n---\n".join(parts)


async def run_react_agent(
    question: str,
    llm_client,
    max_iterations: int = 3,
) -> dict:
    """Run the ReAct agent loop.

    Args:
        question: The user's question.
        llm_client: OpenAI-compatible client instance.
        max_iterations: Maximum tool call iterations.

    Returns:
        dict with keys: answer, sources, confidence, answered_at
    """
    if llm_client is None:
        return _no_llm_response(question)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tools = get_openai_tools()
    all_sources = []
    iteration = 0

    try:
        while iteration < max_iterations:
            iteration += 1

            response = llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=1500,
            )

            if not response or not response.choices:
                logger.error("LLM returned empty response")
                return _no_llm_response(question)

            choice = response.choices[0]
            if not choice or not choice.message:
                logger.error("LLM response missing message")
                return _no_llm_response(question)

            msg = choice.message

            # If the LLM wants to call tools
            if msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    tool = get_tool_by_name(tool_name)

                    if tool is None:
                        result_text = f"Unknown tool: {tool_name}"
                    else:
                        try:
                            args = json.loads(tc.function.arguments)
                            output = tool.run(**args)

                            # Track sources
                            if hasattr(output, "results"):
                                for r in output.results:
                                    src = {
                                        "document_id": r.document_id,
                                        "filename": r.filename,
                                        "page": r.page_number,
                                        "relevance_score": r.score,
                                    }
                                    if src not in all_sources:
                                        all_sources.append(src)

                            result_text = _format_search_results(output)
                        except Exception as e:
                            logger.error(f"Tool {tool_name} execution failed: {e}")
                            result_text = f"Tool execution error: {str(e)}"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    })

                continue

            # No tool calls — this is the final answer
            answer_text = msg.content or ""
            if not answer_text.strip():
                answer_text = "I don't have that information in the available documents."

            confidence = _compute_confidence(all_sources, answer_text)
            return {
                "question": question,
                "answer": answer_text,
                "confidence": confidence,
                "sources": all_sources[:8],
                "answered_at": datetime.now(timezone.utc).isoformat(),
            }

        # Max iterations reached — force final answer
        messages.append({
            "role": "user",
            "content": "You've used all your search attempts. Based on what you've found, give me your best answer. "
                        "If you don't have enough information, say so clearly."
        })
        final = llm_client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
        )
        answer_text = final.choices[0].message.content or "I don't have enough information to answer that question."
        confidence = _compute_confidence(all_sources, answer_text)
        return {
            "question": question,
            "answer": answer_text,
            "confidence": confidence,
            "sources": all_sources[:8],
            "answered_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"ReAct agent failed: {e}")
        return _no_llm_response(question)


def _compute_confidence(sources: list, answer: str) -> int:
    """Heuristic confidence based on sources and answer quality."""
    if not sources:
        return 10
    if "don't have that information" in answer.lower() or "don't have enough" in answer.lower():
        return 15
    base = min(95, len(sources) * 15 + 40)
    return base


def _no_llm_response(question: str) -> dict:
    """Clean response when LLM is unavailable — no raw snippet dumps."""
    return {
        "question": question,
        "answer": "I'm unable to access my knowledge base right now. "
                   "The AI service is not responding — check your API key and try again later.",
        "confidence": 0,
        "sources": [],
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }

"""Chat assistant — utility functions for search context and fallback answers."""

from datetime import datetime, timezone
from backend.logging_config import logger


def _load_chat_prompt() -> str:
    from backend.config import settings
    prompt_path = settings.prompts_dir / "chat_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    logger.warning(f"Chat prompt file not found at {prompt_path}, using inline fallback")
    return ""  # inline not needed — ReAct agent handles it


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


def _fallback_answer(question: str, results: list[dict]) -> str:
    if not results:
        return "I couldn't find relevant information to answer this question. Please try rephrasing or check if the relevant documents have been uploaded."
    lines = ["Based on the available documents, here's what I found:\n"]
    for i, r in enumerate(results[:3]):
        lines.append(f"- {r.get('snippet', '')[:150]}...")
    return "\n".join(lines)


async def generate_answer(question: str, search_results: list | None = None, llm_client=None) -> dict:
    if llm_client is None:
        from backend.llm.client import create_llm_client
        llm_client = create_llm_client()

    from backend.agent.react_agent import run_react_agent
    return await run_react_agent(question, llm_client)

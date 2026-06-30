from openai import OpenAI
from backend.config import settings
from backend.logging_config import logger


def create_llm_client() -> OpenAI | None:
    if not settings.llm_api_key:
        logger.warning("LLM_API_KEY not set; LLM features will use fallback responses")
        return None

    try:
        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create LLM client: {e}")
        return None

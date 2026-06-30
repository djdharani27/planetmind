from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.search.hybrid_search import hybrid_search
from backend.llm.chat_assistant import generate_answer
from backend.logging_config import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    top_k: int = 10
    stream: bool = False


@router.post("")
async def chat(request: ChatRequest):
    try:
        search_results = hybrid_search(request.question, request.top_k)["results"]
        answer = generate_answer(request.question, search_results)
        return answer
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(500, str(e))

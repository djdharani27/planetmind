from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.search.hybrid_search import hybrid_search
from backend.llm.chat_assistant import generate_answer, build_context, CHAT_SYSTEM_PROMPT
from backend.logging_config import logger
import json

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


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    try:
        search_results = hybrid_search(request.question, request.top_k)["results"]
    except Exception as e:
        raise HTTPException(500, str(e))

    async def event_stream():
        context = build_context(search_results)
        answer = generate_answer(request.question, search_results)
        words = answer["answer"].split()
        yield f"data: {json.dumps({'type': 'meta', 'confidence': answer['confidence'], 'sources': answer['sources']})}\n\n"
        for i, word in enumerate(words):
            yield f"data: {json.dumps({'type': 'token', 'text': word + ' ', 'index': i})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


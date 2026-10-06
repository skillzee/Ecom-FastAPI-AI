import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import generate_reply

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = await asyncio.wait_for(generate_reply(request.message, request.history), timeout=45)
    except Exception:
        # Avoid exposing provider credentials or logging shopper messages.
        logger.warning("Shopping assistant request failed")
        raise HTTPException(
            status_code=503,
            detail="The shopping assistant is temporarily unavailable. Please try again shortly.",
        ) from None
    return ChatResponse(reply=reply)

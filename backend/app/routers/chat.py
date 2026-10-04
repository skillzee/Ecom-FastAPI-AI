from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import generate_reply

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    reply = await generate_reply(request.message)
    return ChatResponse(reply=reply)
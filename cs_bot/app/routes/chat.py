import uuid
from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse
from app.services.session_service import get_history, save_history, delete_history
from app.services.rag_service import generate_reply
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    # Load history from Redis
    history = await get_history(session_id)

    # Generate reply via RAG
    reply, sources = await generate_reply(req.message, history)

    # Append new turn to history and persist
    history.append(HumanMessage(content=req.message))
    history.append(AIMessage(content=reply))
    await save_history(session_id, history)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        sources=sources,
    )

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    await delete_history(session_id)
    return {"status": "session cleared", "session_id": session_id}

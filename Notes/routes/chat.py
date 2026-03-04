from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
import logging
from utils.auth import get_current_user, AuthUser

from db import get_session
from services.gemini_service import GeminiService
from services.embedding_service import get_relevant_chunks_for_notebook
from utils.session_memory import SessionMemory
from schemas import ChatRequest, ChatResponse, ChatMessage, ContextChunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

session_memory = SessionMemory()
gemini_service = GeminiService()


@router.post("/{notebook_id}", response_model=ChatResponse)
async def chat_with_notebook(
    notebook_id: UUID,
    chat_request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    user: AuthUser = Depends(get_current_user)
):
    try:
        user_id = user.user_id
        session_id = f"{user_id}_{notebook_id}"

        logger.info(f"Processing chat request for notebook {notebook_id}, user {user_id}")
        logger.info(f"User query: {chat_request.user_query[:100]}...")

        # Step 1: Retrieve relevant chunks
        logger.info("Step 1: Retrieving relevant content chunks...")
        try:
            relevant_chunks = await get_relevant_chunks_for_notebook(
                session=session,
                notebook_id=str(notebook_id),
                user_query=chat_request.user_query,
                top_n=3,        # reduced from 5 — leaves more token budget for output
                min_score=0.6,  # stricter — only high-relevance chunks reach Gemini
                user_id=user_id
            )

            if not relevant_chunks:
                logger.warning(f"No relevant chunks found for notebook {notebook_id}")
                raise HTTPException(
                    status_code=404,
                    detail="No content found in this notebook. Please upload some sources first."
                )

            logger.info(f"Found {len(relevant_chunks)} relevant chunks")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve content: {str(e)}")

        # Step 2: Get existing chat history
        chat_history = session_memory.get_history(session_id)
        logger.info(f"Retrieved chat history with {len(chat_history)} messages")

        # Step 3: Generate response
        # Removed max_tokens cap entirely — gemini_service enforces safe_max_output_tokens=8192
        # Never pass a low max_tokens here — it only causes truncation
        logger.info("Step 2: Generating response with Gemini AI...")
        try:
            ai_response = await gemini_service.generate_contextual_response(
                user_query=chat_request.user_query,
                context_chunks=relevant_chunks,
                chat_history=chat_history,
                # max_tokens intentionally omitted — let gemini_service use 8192 default
            )

            logger.info(f"Generated response: {ai_response[:100]}...")

        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")

        # Step 4: Update chat history
        session_memory.add_message(session_id, "user", chat_request.user_query)
        session_memory.add_message(session_id, "assistant", ai_response)

        # Step 5: Format context chunks for response
        context_used = [
            ContextChunk(
                source_id=chunk["source_id"],
                source_name=chunk["source_name"],
                snippet=chunk["chunk"][:300] + "..." if len(chunk["chunk"]) > 300 else chunk["chunk"],
                similarity_score=chunk["score"]
            )
            for chunk in relevant_chunks
        ]

        # Step 6: Return structured response
        response = ChatResponse(
            answer=ai_response,
            context_used=context_used,
            history=session_memory.get_history(session_id),  # single call, removed redundant step
            notebook_id=str(notebook_id),
            total_chunks_found=len(relevant_chunks),
        )

        logger.info(f"Successfully processed chat request for notebook {notebook_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{notebook_id}/history", response_model=List[ChatMessage])
async def get_chat_history(
    notebook_id: UUID,
    user: AuthUser = Depends(get_current_user),
):
    try:
        session_id = f"{user.user_id}_{notebook_id}"
        history = session_memory.get_history(session_id)
        logger.info(f"Retrieved {len(history)} messages for notebook {notebook_id}")
        return history

    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@router.delete("/{notebook_id}/history")
async def clear_chat_history(
    notebook_id: UUID,
    user: AuthUser = Depends(get_current_user),
):
    try:
        session_id = f"{user.user_id}_{notebook_id}"
        session_memory.clear_history(session_id)
        logger.info(f"Cleared chat history for notebook {notebook_id}")
        return {"message": "Chat history cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")

from fastapi import APIRouter, HTTPException, Depends, status
from app.models.schemas import ChatRequest, ChatResponse, RetrievedChunk, ChatMode
from app.utils.embeddings import embed_query
from app.utils.faiss_handler import get_faiss_store
from app.utils.gemini_handler import get_gemini_handler
from app.utils.auth import get_current_user, AuthUser
from app.utils.session_memory import session_memory

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, user: AuthUser = Depends(get_current_user)):
    """Handle chat requests with general or RAG mode."""
    try:
        session_id = request.session_id or str(user.user_id)
        
        # Retrieve conversation history for the session
        history = session_memory.get_history(session_id)
        
        # Append the current user message to history
        session_memory.append_message(session_id, 'user', request.query)

        gemini_handler = get_gemini_handler()
        
        if request.mode == ChatMode.GENERAL:
            # In general mode, use all previous messages as context
            context = " ".join(m.content for m in history)
            answer = gemini_handler.generate_response(context)
            
            # Store assistant's answer in history
            session_memory.append_message(session_id, 'assistant', answer)
            
            return ChatResponse(
                answer=answer,
                mode=request.mode,
                retrieved_chunks=None
            )

        elif request.mode == ChatMode.RAG:
            # RAG mode - retrieve context first
            faiss_store = get_faiss_store()
            if faiss_store.index.ntotal == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No documents uploaded yet. Please upload documents first."
                )
            # Create embedding for query
            query_embedding = embed_query(request.query)
            
            # Retrieve relevant document chunks for the RAG context
            retrieved_docs = faiss_store.search(query_embedding, k=request.top_k)
            
            if not retrieved_docs:
                # Fallback to general mode if nothing found
                answer = gemini_handler.generate_response(request.query)
                session_memory.append_message(session_id, 'assistant', answer)  # Still record response
                return ChatResponse(
                    answer=f"No relevant documents found. Here's a general response:\n\n{answer}",
                    mode=request.mode,
                    retrieved_chunks=[]
                )
            # Prepare the context from retrieved chunks
            doc_contexts = [doc[0] for doc in retrieved_docs]
            retrieved_chunks = [
                RetrievedChunk(text=doc[0][:200] + "...", source=doc[1], score=doc[2])
                for doc in retrieved_docs
            ]
            
            # Optionally, combine both session history and RAG doc context
            full_context = ["user: " + m.content for m in history] + ["doc: " + c for c in doc_contexts]
            answer = gemini_handler.generate_response(request.query, full_context)
            session_memory.append_message(session_id, 'assistant', answer)  # Store response
            
            return ChatResponse(
                answer=answer,
                mode=request.mode,
                retrieved_chunks=retrieved_chunks
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@router.get("/modes")
async def get_chat_modes():
    """Get available chat modes."""
    return {
        "modes": [
            {"value": "general", "label": "General Chat"},
            {"value": "rag", "label": "Document Chat (RAG)"}
        ]
    }

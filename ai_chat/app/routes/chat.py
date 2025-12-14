from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from app.models.schemas import ChatRequest, ChatResponse, RetrievedChunk, ChatMode
from app.utils.embeddings import embed_query
from app.utils.faiss_handler import get_faiss_store
from app.utils.gemini_handler import get_gemini_handler
from app.utils.auth import get_current_user, AuthUser
from app.utils.session_memory import session_memory
from app.utils.moderation import contains_harmful_content 

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, user: AuthUser = Depends(get_current_user)):
    """Handle chat requests with general or RAG mode."""
    # Guardrail: pre-check user query for harmful content
    # Pre-check: Block on user query before calling Gemini
    if contains_harmful_content(request.query):
        return ChatResponse(
            answer="Your request cannot be processed due to inappropriate content.",
            mode=request.mode,
            retrieved_chunks=None
        )
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
            
            # Post-check: Block on LLM output
            if contains_harmful_content(answer):
                answer = "Sorry, I cannot provide a response due to content policy."
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

@router.post("/solve-image", response_model=ChatResponse)
async def solve_image_question(
    file: UploadFile = File(...),
    subject: str | None = None,
    mode: str | None = "steps",
    current_user=Depends(get_current_user),
):
    """
    Accept a screenshot/photo of a question and return an AI‑generated solution.

    - `subject` is optional (e.g., "math", "physics")
    - `mode` can be "steps" or "final"
    """
    if file.content_type not in {"image/png", "image/jpeg", "image/jpg"}:
        raise HTTPException(
            status_code=400,
            detail="Only PNG and JPEG image uploads are supported for now.",
        )

    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")

        gemini = get_gemini_handler()
        answer_text = await gemini.generate_image_answer(
            image_bytes,
            subject=subject,
            mode=mode,
        )

        # Reuse your existing ChatResponse model: set answer in `response`
        return ChatResponse(
            answer=answer_text,
            mode=ChatMode.GENERAL,          # or ChatMode.RAG, but must be one of these
            retrieved_chunks=None,
            token_count=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error while solving image question: {str(e)}",
        )
    
@router.get("/modes")
async def get_chat_modes():
    """Get available chat modes."""
    return {
        "modes": [
            {"value": "general", "label": "General Chat"},
            {"value": "rag", "label": "Document Chat (RAG)"}
        ]
    }

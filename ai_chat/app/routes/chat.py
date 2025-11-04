from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, RetrievedChunk, ChatMode
from app.utils.embeddings import embed_query
from app.utils.faiss_handler import get_faiss_store
from app.utils.gemini_handler import get_gemini_handler

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with general or RAG mode."""
    try:
        gemini_handler = get_gemini_handler()
        
        if request.mode == ChatMode.GENERAL:
            # General chat mode - direct to Gemini
            answer = gemini_handler.generate_response(request.query)
            
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
            
            # Generate query embedding
            query_embedding = embed_query(request.query)
            
            # Retrieve relevant chunks
            retrieved_docs = faiss_store.search(query_embedding, k=request.top_k)
            
            if not retrieved_docs:
                # No relevant documents found, fall back to general mode
                answer = gemini_handler.generate_response(request.query)
                return ChatResponse(
                    answer=f"No relevant documents found. Here's a general response:\n\n{answer}",
                    mode=request.mode,
                    retrieved_chunks=[]
                )
            
            # Prepare context and retrieved chunks info
            context = [doc[0] for doc in retrieved_docs]
            retrieved_chunks = [
                RetrievedChunk(text=doc[0][:200] + "...", source=doc[1], score=doc[2])
                for doc in retrieved_docs
            ]
            
            # Generate response with context
            answer = gemini_handler.generate_response(request.query, context)
            
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

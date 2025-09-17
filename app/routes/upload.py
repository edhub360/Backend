from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from app.models.schemas import UploadResponse
from app.utils.text_processing import extract_text, chunk_text
from app.utils.embeddings import embed_texts
from app.utils.faiss_handler import get_faiss_store

router = APIRouter()

@router.post("", response_model=UploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload and process documents for RAG."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    total_chunks = 0
    processed_files = 0
    
    for file in files:
        try:
            # Read file content
            file_bytes = await file.read()
            
            # Extract text
            text = extract_text(file.filename, file_bytes)
            
            if not text.strip():
                continue
            
            # Chunk text
            chunks = chunk_text(text)
            
            if not chunks:
                continue
            
            # Generate embeddings
            embeddings = embed_texts(chunks)
            
            # Add to FAISS store
            faiss_store = get_faiss_store(dimension=embeddings.shape[1])
            faiss_store.add_documents(embeddings, chunks, file.filename)
            
            total_chunks += len(chunks)
            processed_files += 1
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing {file.filename}: {str(e)}")
    
    return UploadResponse(
        message=f"Successfully processed {processed_files} files",
        files_processed=processed_files,
        total_chunks_added=total_chunks
    )

@router.get("/stats")
async def get_upload_stats():
    """Get statistics about uploaded documents."""
    faiss_store = get_faiss_store()
    return faiss_store.get_stats()

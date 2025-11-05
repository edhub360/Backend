from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

class ChatMode(str, Enum):
    GENERAL = "general"
    RAG = "rag"

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query")
    mode: ChatMode = Field(..., description="Chat mode: general or rag")
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks to retrieve for RAG")
    session_id: Optional[str] = Field(None, description="Optional session identifier for conversation context")
class RetrievedChunk(BaseModel):
    text: str
    source: str
    score: float

class ChatResponse(BaseModel):
    answer: str
    mode: ChatMode
    retrieved_chunks: Optional[List[RetrievedChunk]] = None
    token_count: Optional[int] = None

class UploadResponse(BaseModel):
    message: str
    files_processed: int
    total_chunks_added: int

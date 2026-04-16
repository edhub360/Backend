from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID


class NotebookCreate(BaseModel):
    title: str


class Notebook(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    user_id: str


class SourceCreate(BaseModel):
    type: str  # 'file', 'website', 'youtube'
    filename: Optional[str] = None
    file_url: Optional[str] = None
    website_url: Optional[str] = None
    youtube_url: Optional[str] = None
    metadata: Optional[dict] = None


class Source(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notebook_id: UUID
    type: str
    filename: Optional[str] = None
    file_url: Optional[str] = None
    website_url: Optional[str] = None
    youtube_url: Optional[str] = None
    extracted_text: Optional[str] = None


class EmbeddingChunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chunk: str
    score: Optional[float] = None


class SemanticSearchRequest(BaseModel):
    query: str
    notebook_id: str
    top_n: int = 5
    source_ids: Optional[List[UUID]] = None


class SemanticSearchResult(BaseModel):
    id: str
    chunk: str
    source_id: str
    score: float


class SemanticSearchResponse(BaseModel):
    chunks: List[EmbeddingChunk]


class ChatRequest(BaseModel):
    user_query: str
    max_context_chunks: Optional[int] = 5
    max_tokens: Optional[int] = 512


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str


class ContextChunk(BaseModel):
    source_id: str
    source_name: str
    snippet: str
    similarity_score: float


class ChatResponse(BaseModel):
    answer: str
    context_used: List[ContextChunk]
    history: List[ChatMessage]
    notebook_id: str
    total_chunks_found: int
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

class NotebookCreate(BaseModel):
    title: str

class Notebook(BaseModel):
    id: UUID
    title: str
    user_id: str
    class Config:
        from_attributes = True

class SourceCreate(BaseModel):
    type: str  # 'file', 'website', 'youtube'
    filename: Optional[str]
    file_url: Optional[str]
    website_url: Optional[str]
    youtube_url: Optional[str]
    metadata: Optional[dict]

class Source(BaseModel):
    id: UUID
    notebook_id: UUID
    type: str
    filename: Optional[str]
    file_url: Optional[str]
    website_url: Optional[str]
    youtube_url: Optional[str]
    extracted_text: Optional[str]
    class Config:
        from_attributes = True

class EmbeddingChunk(BaseModel):
    id: UUID
    chunk: str
    score: Optional[float]
    class Config:
        from_attributes = True

class SemanticSearchRequest(BaseModel):
    query: str
    top_n: int = 5
    source_ids: Optional[List[UUID]]

class SemanticSearchResponse(BaseModel):
    chunks: List[EmbeddingChunk]

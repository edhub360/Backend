from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources: list[str]

class IngestRequest(BaseModel):
    urls: list[str]

class IngestResponse(BaseModel):
    status: str
    urls: list[str]
    chunks_added: int

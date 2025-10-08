from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from schemas import SemanticSearchRequest, SemanticSearchResponse
from services.embedding_service import semantic_search

router = APIRouter()

@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def search_embeddings(
    data: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
):
    return await semantic_search(data, session)

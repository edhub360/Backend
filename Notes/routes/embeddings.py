from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from Notes.db import get_session
from Notes.schemas import SemanticSearchRequest, SemanticSearchResponse
from Notes.services.embedding_service import semantic_search
from Notes.utils.auth import get_current_user, AuthUser

router = APIRouter()

@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def search_embeddings(
    data: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
    user: AuthUser = Depends(get_current_user), 
):
    return await semantic_search(data, session, user.user_id)

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from utils.auth import get_current_user, AuthUser
from schemas import SemanticSearchRequest
from services.embedding_service import semantic_search


router = APIRouter()


@router.post("/semantic-search")
async def search_embeddings(
    request: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
    user: AuthUser = Depends(get_current_user),
):
    return await semantic_search(request, session, user.user_id)
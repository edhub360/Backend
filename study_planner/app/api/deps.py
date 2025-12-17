from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db


DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]

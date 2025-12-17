from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db

DBSessionDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]

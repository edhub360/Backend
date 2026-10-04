# auth.py - verifies the shared platform JWT (same JWT_SECRET_KEY/JWT_ALGORITHM
# every other service trusts) and returns the authenticated user's id.
# No DB round trip here on purpose - this runs on every request.

import os
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ADMIN_KEY = os.getenv("ADMIN_KEY", "")

bearer_scheme = HTTPBearer()


def require_admin(x_admin_key: str = Header(...)) -> None:
    """Gate for internal/ops-only routes (bulk import, etc) - not tied to a
    user account, just a shared secret only the team knows."""
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Decode the bearer token and return the authenticated user_id (sub claim)."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user_id

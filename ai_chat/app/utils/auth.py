import jwt
import os
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone
from typing import Dict


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()


class AuthUser:
    def __init__(self, user_id: int, email: str, username: str, roles: list = None):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.roles = roles if roles is not None else []


def verify_token(token: str) -> Dict:
    try:
        # Disable PyJWT's built-in exp check so we control the error message
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False},  # ← key change
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Manual exp check — now runs for ALL tokens including expired ones
    # payload.get("exp", 0) handles tokens with no exp field (treats as already expired)
    now = datetime.now(timezone.utc).timestamp()
    if payload.get("exp", 0) < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    payload = verify_token(credentials.credentials)
    return AuthUser(
        user_id=payload.get("user_id"),
        email=payload.get("email"),
        username=payload.get("username"),
        roles=payload.get("roles") or [],
    )
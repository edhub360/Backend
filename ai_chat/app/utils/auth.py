import jwt
import os
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
from typing import Optional, Dict

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()

class AuthUser:
    def __init__(self, user_id: int, email: str, username: str, roles: list = None):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.roles = roles or []

def verify_token(token: str) -> Dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if datetime.utcnow().timestamp() > payload.get("exp", 0):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthUser:
    """Extract and validate user from JWT token"""
    payload = verify_token(credentials.credentials)
    return AuthUser(
        user_id=payload.get("user_id"),
        email=payload.get("email"),
        username=payload.get("username"),
        roles=payload.get("roles", [])
    )

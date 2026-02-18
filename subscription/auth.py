from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from uuid import UUID
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from db import get_db
from models import User

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here") # Should match login service
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login") # Point to login service

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            JWT_SECRET_KEY, 
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def enforce_free_plan_expiry(db: AsyncSession, user: User) -> User:
    """
    If user is on free tier and the free plan has expired,
    reset subscription_tier to None, but KEEP free_plan_activated_at
    so we know they already used their one-time free plan.
    """
    if user.subscription_tier == "free" and user.free_plan_expires_at:
        now = datetime.now(timezone.utc)
        expires = user.free_plan_expires_at.astimezone(timezone.utc)

        if now > expires:
            user.subscription_tier = None
            await db.commit()
            await db.refresh(user)

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    try:
        # Decode JWT token
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get user from database
        result = await db.execute(select(User).where(User.user_id == UUID(user_id)))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Enforce free-plan expiry on every authenticated call
        user = await enforce_free_plan_expiry(db, user)
        
        return user
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

"""Core authentication utilities and JWT handling."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
from jose import JWTError, jwt
from passlib.context import CryptContext
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException, status
import httpx  

from app.config import settings
from app.utils import generate_secure_token, hash_token

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Add safety check for bcrypt 72-byte limit
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Add safety check for bcrypt 72-byte limit
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any]) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token() -> tuple[str, str]:
    """Create a refresh token and return both token and hash."""
    token = generate_secure_token(48)
    token_hash = hash_token(token)
    return token, token_hash


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def verify_google_token(token: str) -> Dict[str, Any]:
    """Verify Google OAuth2 access token and return user info."""
    try:
        # Use Google userinfo endpoint instead of id_token verification
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )

        if response.status_code != 200:
            logger.warning(f"Google userinfo request failed: {response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google token"
            )

        idinfo = response.json()

        # Check email verification
        if not idinfo.get('email_verified', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not verified by Google"
            )

        # Extract user info
        user_info = {
            'google_id': idinfo.get('sub'),
            'email': idinfo.get('email'),
            'name': idinfo.get('name'),
            'picture': idinfo.get('picture')
        }

        if not user_info['email']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )

        logger.info(f"Google token verified for user: {user_info['email']}")
        return user_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify Google token"
        )
    
async def verify_microsoft_token(token: str) -> Dict[str, Any]:
    """Verify Microsoft access token via Graph API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token}"},
                params={"$select": "id,displayName,mail,userPrincipalName"}
            )

        if response.status_code != 200:
            logger.warning(f"Microsoft Graph request failed: {response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Microsoft token"
            )

        profile = response.json()

        #  mail can be null for personal accounts — fallback to userPrincipalName
        email = profile.get('mail') or profile.get('userPrincipalName')

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Microsoft"
            )

        return {
            'microsoft_id': profile.get('id'),
            'email': email,
            'name': profile.get('displayName'),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Microsoft token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify Microsoft token"
        )

async def verify_facebook_token(token: str) -> Dict[str, Any]:
    """Verify Facebook access token via Graph API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.facebook.com/me",
                params={
                    "fields": "id,name,email,picture",
                    "access_token": token,
                }
            )

        if response.status_code != 200:
            logger.warning(f"Facebook Graph request failed: {response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Facebook token"
            )

        profile = response.json()

        if "error" in profile:
            logger.warning(f"Facebook token error: {profile['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Facebook token"
            )

        email = profile.get("email")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Facebook account"
            )

        return {
            "facebook_id": profile.get("id"),
            "email": email,
            "name": profile.get("name"),
            "picture": profile.get("picture", {}).get("data", {}).get("url"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Facebook token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify Facebook token"
        )

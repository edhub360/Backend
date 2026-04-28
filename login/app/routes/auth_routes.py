"""Authentication routes and endpoints."""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from uuid import UUID
import logging
from starlette.requests import Request
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.utils import generate_secure_token, hash_token

from app.db import get_db
from app.models import User, AuthCredential, RefreshToken, PasswordResetToken
from app.schemas import (
    GoogleSignInRequest, EmailRegisterRequest, EmailLoginRequest, FacebookLoginRequest,
    TokenResponse, RefreshTokenRequest, LogoutRequest, UserResponse, UserUpdate, MicrosoftSignInRequest
)
from app.auth import (
    verify_google_token, hash_password, verify_password,
    create_access_token, create_refresh_token, decode_jwt_token, verify_microsoft_token, verify_facebook_token
)
from app.config import settings

MAX_SESSIONS_PER_USER = 3

logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


from typing import Dict, Any, Optional

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()



async def create_user(db: AsyncSession, email: str, name: str = None) -> User:
    """Create a new user."""
    user = User(email=email, name=name)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_auth_credential(
    db: AsyncSession, 
    user_id: UUID, 
    provider: str, 
    password_hash: str = None
) -> AuthCredential:
    """Create authentication credential."""
    credential = AuthCredential(
        user_id=user_id,
        provider=provider,
        password_hash=password_hash
    )
    db.add(credential)
    await db.flush()
    return credential

async def create_refresh_token_db(
    db: AsyncSession,
    user_id: UUID,
    token_hash: str
) -> RefreshToken:
    """Create refresh token — single session per user, revokes previous on new login."""

    # Revoke all existing active sessions
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
        .values(revoked=True)
    )
    logger.info(f"Previous sessions revoked for user {user_id}")

    # Create new session
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(refresh_token)
    await db.flush()
    return refresh_token

async def create_password_reset_token_db(
    db: AsyncSession,
    user_id: UUID,
    token_hash: str,
) -> PasswordResetToken:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    prt = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(prt)
    await db.flush()
    return prt


async def generate_tokens(db: AsyncSession, user: User) -> Dict[str, Any]:
    """Generate access and refresh tokens for user."""
    # Create access token
    access_token_data = {
        "sub": str(user.user_id),
        "user_id": str(user.user_id),
        "email": user.email,
        "name": user.name,
        "subscription_tier": user.subscription_tier or None
    }
    access_token = create_access_token(access_token_data)
    
    # Create refresh token
    refresh_token, refresh_token_hash = create_refresh_token()
    await create_refresh_token_db(db, user.user_id, refresh_token_hash)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": UserResponse.from_orm(user)
    }


@router.post("/google", response_model=TokenResponse)
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def google_signin(
    google_request: GoogleSignInRequest,  # Renamed to avoid confusion
    request: Request,  # Add this - required by SlowAPI
    db: AsyncSession = Depends(get_db)
):
    """Google Sign-In authentication endpoint."""
    try:
        # Verify Google token
        user_info = await verify_google_token(google_request.token)
        
        # Check if user exists
        user = await get_user_by_email(db, user_info['email'])
        
        if user:
            # Update name if changed
            if user.name != user_info['name']:
                user.name = user_info['name']
                await db.flush()
        else:
            # Create new user
            user = await create_user(db, user_info['email'], user_info['name'])
            # Create auth credential for Google provider
            await create_auth_credential(db, user.user_id, "google")
        
        # Generate tokens
        tokens = await generate_tokens(db, user)
        is_first_login = not user.subscription_tier 
        
        logger.info(f"Google sign-in successful for user: {user.email}")
        return TokenResponse(**tokens, is_first_login=is_first_login)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google sign-in error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.post("/microsoft", response_model=TokenResponse)
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def microsoft_signin(
    microsoft_request: MicrosoftSignInRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Microsoft Sign-In authentication endpoint."""
    try:
        user_info = await verify_microsoft_token(microsoft_request.token)

        user = await get_user_by_email(db, user_info['email'])
        is_new_user = user is None  #  track before any DB ops

        if user:
            if user.name != user_info['name']:
                user.name = user_info['name']
                await db.flush()
            await db.refresh(user)  #  avoid stale subscription_tier
        else:
            user = await create_user(db, user_info['email'], user_info['name'])
            await create_auth_credential(db, user.user_id, "microsoft")

        tokens = await generate_tokens(db, user)
        is_first_login = is_new_user or not user.subscription_tier

        logger.info(f"Microsoft sign-in successful for user: {user.email}")
        return TokenResponse(**tokens, is_first_login=is_first_login)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Microsoft sign-in error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.post("/facebook", response_model=TokenResponse)
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def facebook_signin(
    facebook_request: FacebookLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Facebook Sign-In authentication endpoint."""
    try:
        user_info = await verify_facebook_token(facebook_request.token)

        user = await get_user_by_email(db, user_info['email'])
        is_new_user = user is None

        if user:
            if user.name != user_info['name']:
                user.name = user_info['name']
                await db.flush()
            await db.refresh(user)
        else:
            user = await create_user(db, user_info['email'], user_info['name'])
            await create_auth_credential(db, user.user_id, "facebook")

        tokens = await generate_tokens(db, user)
        is_first_login = is_new_user or not user.subscription_tier

        logger.info(f"Facebook sign-in successful for user: {user.email}")
        return TokenResponse(**tokens, is_first_login=is_first_login)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Facebook sign-in error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/register", response_model=TokenResponse)
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def register(
    register_request: EmailRegisterRequest,  # Renamed 
    request: Request,  # Add this - required by SlowAPI
    db: AsyncSession = Depends(get_db)
):
    """Email registration endpoint."""
    try:
        # Check if user already exists
        existing_user = await get_user_by_email(db, register_request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        user = await create_user(db, register_request.email, register_request.name)
        
        # Hash password and create auth credential
        password_hash = hash_password(register_request.password)
        await create_auth_credential(db, user.user_id, "email", password_hash)
        
        # Generate tokens
        tokens = await generate_tokens(db, user)
        is_first_login = True  # New user
        
        logger.info(f"User registration successful for: {user.email}")
        return TokenResponse(**tokens, is_first_login=is_first_login)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def login(
    login_request: EmailLoginRequest,  # Renamed
    request: Request,  # Add this - required by SlowAPI
    db: AsyncSession = Depends(get_db)
):
    """Email login endpoint."""
    try:
        # Get user
        user = await get_user_by_email(db, login_request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get auth credential
        result = await db.execute(
            select(AuthCredential).where(
                AuthCredential.user_id == user.user_id,
                AuthCredential.provider == "email"
            )
        )
        auth_cred = result.scalar_one_or_none()
        
        if not auth_cred or not auth_cred.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(login_request.password, auth_cred.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate tokens
        tokens = await generate_tokens(db, user)
        is_first_login = not user.subscription_tier 
        
        logger.info(f"Login successful for user: {user.email}")
        return TokenResponse(**tokens, is_first_login=is_first_login)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        token_hash = hash_token(refresh_request.refresh_token)

        # Find token WITHOUT revoked/expiry filters — check separately
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        refresh_token_record = result.scalar_one_or_none()

        if not refresh_token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Distinguish revoked (another device) vs expired (timeout)
        if refresh_token_record.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to login from another device"
            )

        if refresh_token_record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired, please log in again"
            )

        # Get user
        result = await db.execute(
            select(User).where(User.user_id == refresh_token_record.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Revoke old refresh token (token rotation)
        refresh_token_record.revoked = True

        # Generate new tokens
        tokens = await generate_tokens(db, user)

        logger.info(f"Token refresh successful for user: {user.email}")
        return TokenResponse(**tokens)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/session/check")
async def check_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Lightweight session validity check — no token rotation."""
    refresh_token_value = request.headers.get("X-Refresh-Token")
    if not refresh_token_value:
        return JSONResponse(status_code=401, content={"valid": False, "detail": "No refresh token provided"})  # ✅ return, not raise

    token_hash = hash_token(refresh_token_value)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        return JSONResponse(status_code=401, content={"valid": False, "detail": "Invalid refresh token"})

    if token_record.revoked:
        return JSONResponse(status_code=401, content={"valid": False, "detail": "Session expired due to login from another device"})

    if token_record.expires_at < datetime.now(timezone.utc):
        return JSONResponse(status_code=401, content={"valid": False, "detail": "Session expired, please log in again"})

    return {"valid": True}

@router.post("/logout")
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def logout(
    logout_request: LogoutRequest,  # Renamed
    request: Request,  # Add this - required by SlowAPI
    db: AsyncSession = Depends(get_db)
):
    try:
        token_hash = hash_token(logout_request.refresh_token)
        
        # Find and revoke refresh token
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        refresh_token_record = result.scalar_one_or_none()
        
        if refresh_token_record:
            refresh_token_record.revoked = True
            await db.flush()
            logger.info(f"Logout successful for user_id: {refresh_token_record.user_id}")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


async def enforce_free_plan_expiry(db: AsyncSession, user: User) -> User:
    """
    Checks if the user's free plan has expired on every request.
    If expired, sets subscription_tier to None so access is blocked immediately.
    Does NOT reset free_plan_activated_at — that stays forever to block re-activation.
    """
    if (
        user.subscription_tier == "free"
        and user.free_plan_expires_at is not None
    ):
        now = datetime.now(timezone.utc)
        expires = user.free_plan_expires_at.replace(tzinfo=timezone.utc)

        if now > expires:
            user.subscription_tier = None  # Revoke access
            # DO NOT touch free_plan_activated_at — keeps the one-time gate intact
            await db.commit()
            await db.refresh(user)
            print(f"⏰ Free plan expired for user {user.email} — tier reset to None")

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        result = await db.execute(select(User).where(User.user_id == UUID(user_id)))
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # ✅ Auto-expire free plan on every authenticated request
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
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile - protected endpoint example."""
    return UserResponse.from_orm(current_user)

@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update current user's profile (currently only name).
    """
    user = current_user

    if payload.name is not None:
        user.name = payload.name

    await db.flush()
    await db.refresh(user)

    return UserResponse.from_orm(user)


#  NEW ENDPOINT - Activate Subscription


# Add rate limit handler
#router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

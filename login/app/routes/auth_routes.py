"""Authentication routes and endpoints."""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from uuid import UUID
import logging
from starlette.requests import Request
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.utils import generate_secure_token, hash_token

from app.db import get_db
from app.models import User, AuthCredential, RefreshToken, PasswordResetToken
from app.schemas import (
    GoogleSignInRequest, EmailRegisterRequest, EmailLoginRequest,
    TokenResponse, RefreshTokenRequest, LogoutRequest, UserResponse
)
from app.auth import (
    verify_google_token, hash_password, verify_password,
    create_access_token, create_refresh_token, decode_jwt_token
)
from app.config import settings

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
    """Create refresh token in database."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(refresh_token)
    await db.flush()
    return refresh_token


from datetime import datetime, timedelta, timezone

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
    request: Request,  # ✅ Add this - required by SlowAPI
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


@router.post("/register", response_model=TokenResponse)
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def register(
    register_request: EmailRegisterRequest,  # Renamed 
    request: Request,  # ✅ Add this - required by SlowAPI
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
    request: Request,  # ✅ Add this - required by SlowAPI
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
    refresh_request: RefreshTokenRequest,  # Renamed
    request: Request,  # ✅ Add this - required by SlowAPI
    db: AsyncSession = Depends(get_db)
):
    try:
        token_hash = hash_token(refresh_request.refresh_token)
        
        # Find refresh token
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc)
            )
        )
        refresh_token_record = result.scalar_one_or_none()
        
        if not refresh_token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
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
        
        # Revoke old refresh token
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


@router.post("/logout")
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def logout(
    logout_request: LogoutRequest,  # Renamed
    request: Request,  # ✅ Add this - required by SlowAPI
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


# Dependency for current user
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

#  NEW ENDPOINT - Activate Subscription
@router.post("/activate-subscription")
async def activate_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate free trial subscription for first-time users."""
    print(f"\n{'='*60}")
    print(f" DEBUG: ACTIVATE SUBSCRIPTION endpoint called")
    print(f" DEBUG: User: {current_user.email}")
    print(f" DEBUG: Current subscription_tier: {current_user.subscription_tier}")
    print(f"{'='*60}\n")
    
    try:
        # Check if already has subscription
        if current_user.subscription_tier:
            print(f" DEBUG: Subscription already active")
            return {
                "message": "Subscription already active",
                "subscription_tier": current_user.subscription_tier,
                "status": "already_active"
            }
        
        print(f" DEBUG: Setting subscription_tier to 'free'...")
        # Activate free trial
        current_user.subscription_tier = 'free'
        
        print(f" DEBUG: Committing to database...")
        await db.commit()
        await db.refresh(current_user)
        
        print(f" DEBUG: Free trial activated successfully!")
        logger.info(f" Free trial activated for user: {current_user.email}")
        
        return {
            "message": "Free trial activated successfully",
            "subscription_tier": "free",
            "status": "activated"
        }
        
    except Exception as e:
        print(f" DEBUG: Activation error: {str(e)}")
        await db.rollback()
        logger.error(f" Subscription activation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate subscription"
        )

# Add rate limit handler
#router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

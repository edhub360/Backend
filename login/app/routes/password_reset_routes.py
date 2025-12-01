"""Password reset routes (forgot/reset password)."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models import User, AuthCredential, PasswordResetToken
from app.schemas import ForgotPasswordRequest, ResetPasswordRequest
from app.auth import hash_password
from app.utils import generate_secure_token, hash_token
from app.config import settings
from app.email_utils import send_reset_password_email
from app.routes.auth_routes import limiter  # or wherever you expose Limiter

logger = logging.getLogger(__name__)

password_reset_router = APIRouter()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


@password_reset_router.post("/forgot-password")
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Start forgot-password flow.

    - Always returns 200 with a generic message to avoid user enumeration.
    - If user exists, creates a one-time password reset token, stores its hash,
      and emails a reset link to the user.
    """
    try:
        user = await get_user_by_email(db, payload.email)
        if not user:
            # Do not reveal whether the email exists
            return {
                "message": "If an account exists for this email, a reset link has been sent."
            }

        # Generate raw token and hash
        raw_token = generate_secure_token(48)
        token_hash = hash_token(raw_token)

        # Store reset token (1 hour expiry)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        reset_token = PasswordResetToken(
            user_id=user.user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        # Build reset URL for frontend (normalize trailing slash)
        base_url = str(settings.frontend_base_url).rstrip("/")
        reset_url = f"{base_url}/reset-password?token={raw_token}"

        # Send real email
        send_reset_password_email(user.email, reset_url)

        logger.info(f"Password reset email initiated for {user.email}")
        return {
            "message": "If an account exists for this email, a reset link has been sent."
        }
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        await db.rollback()
        # Still respond generically
        return {
            "message": "If an account exists for this email, a reset link has been sent."
        }


@password_reset_router.post("/reset-password")
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete password reset.

    - Validates the reset token (hash, expiry, not used).
    - Updates the email/password credential's password hash.
    - Marks the reset token as used.
    """
    try:
        token_hash = hash_token(payload.token)

        # Find valid unused reset token
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > datetime.now(timezone.utc),
            )
        )
        reset_record = result.scalar_one_or_none()
        if not reset_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Load user
        result = await db.execute(
            select(User).where(User.user_id == reset_record.user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found",
            )

        # Find email/password credential
        result = await db.execute(
            select(AuthCredential).where(
                AuthCredential.user_id == user.user_id,
                AuthCredential.provider == "email",
            )
        )
        auth_cred = result.scalar_one_or_none()
        if not auth_cred:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email/password login not enabled for this account",
            )

        # Update password and mark token used
        auth_cred.password_hash = hash_password(payload.new_password)
        reset_record.used = True

        await db.commit()
        logger.info(f"Password reset successfully for user {user.email}")

        return {"message": "Password has been reset successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password",
        )

"""Pydantic request/response schemas."""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import uuid


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user creation."""
    pass


class UserResponse(UserBase):
    """Schema for user response."""
    user_id: uuid.UUID
    language: Optional[str] = None
    subscription_tier: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Authentication Schemas
class GoogleSignInRequest(BaseModel):
    """Schema for Google Sign-In request."""
    token: str = Field(..., description="Google ID token from frontend")


class EmailRegisterRequest(BaseModel):
    """Schema for email registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class EmailLoginRequest(BaseModel):
    """Schema for email login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Schema for logout request."""
    refresh_token: str


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
    error_code: Optional[str] = None

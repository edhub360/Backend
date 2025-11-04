"""Configuration management using Pydantic settings."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database settings
    database_url: str = Field(..., description="PostgreSQL database URL")
    db_echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")
    
    # JWT settings
    jwt_secret_key: str = Field(..., description="Secret key for JWT tokens")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(default=15, description="Access token expiry in minutes")
    refresh_token_expire_days: int = Field(default=30, description="Refresh token expiry in days")
    
    # OAuth settings
    google_client_id: str = Field(..., description="Google OAuth client ID")
    
    # Security settings
    bcrypt_rounds: int = Field(default=12, description="Bcrypt hashing rounds")
    rate_limit_requests: int = Field(default=5, description="Rate limit requests per minute")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    
    # App settings
    app_name: str = Field(default="Auth Microservice", description="Application name")
    debug: bool = Field(default=False, description="Enable debug mode")


settings = Settings()

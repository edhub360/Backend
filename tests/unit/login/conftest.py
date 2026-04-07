"""
tests/unit/login/conftest.py
Sets required env vars before any app module is imported.
"""
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-bytes-minimum!!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("GOOGLE_CLIENT_ID", "fake-google-client-id.apps.googleusercontent.com")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("RATE_LIMIT_REQUESTS", "100")
os.environ.setdefault("FRONTEND_BASE_URL", "http://localhost:3000")
os.environ.setdefault("SMTP_HOST", "smtp.example.com")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USER", "test@example.com")
os.environ.setdefault("SMTP_PASSWORD", "smtp-password")
os.environ.setdefault("EMAILS_FROM_EMAIL", "noreply@example.com")
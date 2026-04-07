"""
tests/unit/login/conftest.py
"""
import os
import sys

_here       = os.path.dirname(__file__)                          # tests/unit/login/
_repo_root  = os.path.abspath(os.path.join(_here, "../../.."))  # repo root
_login_root = os.path.join(_repo_root, "login")                 # login/

if _login_root not in sys.path:
    sys.path.insert(0, _login_root)   # ← FRONT of sys.path

os.environ.setdefault("JWT_SECRET_KEY",              "test-secret-key-for-login-tests-32b!")
os.environ.setdefault("JWT_ALGORITHM",               "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS",   "7")
os.environ.setdefault("GOOGLE_CLIENT_ID",            "fake-google-client.apps.googleusercontent.com")
os.environ.setdefault("DATABASE_URL",                "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("RATE_LIMIT_REQUESTS",         "100")
os.environ.setdefault("FRONTEND_BASE_URL",           "http://localhost:3000")
os.environ.setdefault("SMTP_HOST",                   "smtp.example.com")
os.environ.setdefault("SMTP_PORT",                   "587")
os.environ.setdefault("SMTP_USERNAME",               "test@example.com")
os.environ.setdefault("SMTP_PASSWORD",               "smtp-password")
os.environ.setdefault("SMTP_FROM_EMAIL",             "noreply@example.com")
os.environ.setdefault("SMTP_FROM_NAME",              "EdHub360")
os.environ.setdefault("DB_ECHO",                     "false")
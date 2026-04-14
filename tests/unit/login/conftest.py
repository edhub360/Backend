# tests/unit/login/conftest.py
import os, sys

_here      = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_here, "../../.."))
_login_root = os.path.join(_repo_root, "login")

if _login_root not in sys.path:
    sys.path.insert(0, _login_root)

# ── Set env vars BEFORE any app module is imported ──────────────────────────
# pydantic-settings reads from os.environ at Settings() instantiation time.
# These must be set here at module level, not inside a fixture.
os.environ["DATABASE_URL"]                = "postgresql+asyncpg://user:pass@localhost/testdb"
os.environ["JWT_SECRET_KEY"]              = "test-secret-key-for-login-tests-32b!"
os.environ["JWT_ALGORITHM"]               = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"]   = "7"
os.environ["GOOGLE_CLIENT_ID"]            = "fake-google-client.apps.googleusercontent.com"
os.environ["FRONTEND_BASE_URL"]           = "http://localhost:3000"
os.environ["SMTP_HOST"]                   = "smtp.example.com"
os.environ["SMTP_PORT"]                   = "587"
os.environ["SMTP_USERNAME"]               = "test@example.com"
os.environ["SMTP_PASSWORD"]               = "smtp-password"
os.environ["SMTP_FROM_EMAIL"]             = "noreply@example.com"
os.environ["SMTP_FROM_NAME"]              = "EdHub360"
os.environ["DB_ECHO"]                     = "false"
os.environ["RATE_LIMIT_REQUESTS"]         = "100"
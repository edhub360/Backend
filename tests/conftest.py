import os
import sys
import types
from unittest.mock import MagicMock
from sqlalchemy.orm import DeclarativeBase

# ── Env vars (before any service imports) ──────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "fake-secret-key-for-testing")
os.environ.setdefault("GOOGLE_CLIENT_ID", "fake-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "fake-google-client-secret")
os.environ.setdefault("JWT_SECRET_KEY", "fake-jwt-secret-for-testing")
os.environ.setdefault("JWT_SECRET", "fake-jwt-secret-for-testing")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-api-key")
os.environ.setdefault("STRIPE_SECRET_KEY", "fake-stripe-secret-key")

# ── Mock `app.*` bare imports (login service) ─────────────────────
class _TestBase(DeclarativeBase):
    pass

_mock_db = MagicMock()
_mock_db.Base = _TestBase

_mock_cfg = MagicMock()
_mock_cfg.settings.jwt_secret_key = "fake-jwt-secret-for-testing"
_mock_cfg.settings.jwt_algorithm = "HS256"
_mock_cfg.settings.access_token_expire_minutes = 15

_mock_app_pkg = types.ModuleType("app")
sys.modules["app"] = _mock_app_pkg
sys.modules["app.config"] = _mock_cfg
sys.modules["app.db"] = _mock_db
sys.modules["app.utils"] = MagicMock(
    generate_secure_token=MagicMock(return_value="fake-token"),
    hash_token=MagicMock(return_value="fake-hash"),
)

# ── Mock google.cloud.storage ─────────────────────────────────────
_mock_gcs = types.ModuleType("google.cloud.storage")
_mock_gcs.Client = MagicMock()
_google_mod = sys.modules.get("google") or types.ModuleType("google")
_google_cloud_mod = sys.modules.get("google.cloud") or types.ModuleType("google.cloud")
_google_cloud_mod.storage = _mock_gcs
sys.modules["google"] = _google_mod
sys.modules["google.cloud"] = _google_cloud_mod
sys.modules["google.cloud.storage"] = _mock_gcs
sys.modules["pandas"] = MagicMock()

# ── Mock LLM/LangChain dependencies ──────────────────────────────
_mock_langchain = MagicMock()
for _mod in [
    "langchain", "langchain.chains", "langchain.memory", "langchain.prompts",
    "langchain_core", "langchain_core.messages", "langchain_core.prompts",
    "langchain_core.output_parsers", "langchain_google_genai",
    "google.generativeai", "google.generativeai.types",
]:
    sys.modules.setdefault(_mod, MagicMock())

# ── Combined bare `models`, `schemas`, `database` shims ──────────
import quiz.models as _qz_models
import flashcard.models as _fc_models
import quiz.schemas as _qz_schemas
import flashcard.schemas as _fc_schemas
import quiz.database as _qz_db

def _merge_modules(name, *sources):
    mod = types.ModuleType(name)
    for src in sources:
        for attr in dir(src):
            if not attr.startswith("__"):
                setattr(mod, attr, getattr(src, attr))
    sys.modules[name] = mod

_merge_modules("models", _qz_models, _fc_models)
_merge_modules("schemas", _qz_schemas, _fc_schemas)
sys.modules.setdefault("database", _qz_db)
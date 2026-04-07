"""
conftest.py for tests/unit/Notes/

Fixes:
1. sys.path — supports BOTH bare imports (`from db import ...`) AND
   package-prefixed imports (`from Notes.db import ...`)
2. Module aliasing — ensures `Notes.x` and bare `x` resolve to the SAME
   object, so dependency_overrides and patches work correctly
3. Third-party stubs — heavy/unavailable packages are mocked before any
   app code loads (fitz, pgvector, bs4, asyncpg, etc.)
4. create_async_engine shim — strips PostgreSQL-only pool kwargs when
   SQLite is used in tests
5. Eager submodule imports — ensures `services.extract_service` etc. are
   accessible as attributes of their parent package
"""

import sys
import os
import types
import importlib
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Resolve paths
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "../../.."))
_NOTES_ROOT = os.path.join(_REPO_ROOT, "Notes")

for _p in (_NOTES_ROOT, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# 2. Stub heavy / unavailable third-party modules BEFORE any app import
# ---------------------------------------------------------------------------

def _stub(name: str, **attrs):
    parts = name.split(".")
    for i in range(1, len(parts) + 1):
        key = ".".join(parts[:i])
        if key not in sys.modules:
            sys.modules[key] = MagicMock()
    mod = sys.modules[name]
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod

_stub("fitz")

_pgvector_sa = _stub("pgvector.sqlalchemy")
_pgvector_sa.Vector = lambda dim=768: MagicMock()

_stub("asyncpg")

_bs4 = _stub("bs4")
_bs4.BeautifulSoup = MagicMock()

_stub("requests")
_stub("youtube_transcript_api")
_stub("docx")
_stub("pptx")
_stub("openpyxl")
_stub("google.cloud.storage")

# Intentionally do NOT stub google.generativeai here.
# test_gemini_services.py patches the module directly.

# ---------------------------------------------------------------------------
# 3. create_async_engine shim
# ---------------------------------------------------------------------------
try:
    from sqlalchemy.ext.asyncio import create_async_engine as _real_cae
    import sqlalchemy.ext.asyncio as _sa_async

    def _safe_create_async_engine(url, **kwargs):
        if "sqlite" in str(url):
            for key in (
                "pool_size",
                "max_overflow",
                "pool_timeout",
                "pool_recycle",
                "pool_pre_ping",
            ):
                kwargs.pop(key, None)
        return _real_cae(url, **kwargs)

    _sa_async.create_async_engine = _safe_create_async_engine
except ImportError:
    pass

# ---------------------------------------------------------------------------
# 4. Register Notes as a package
# ---------------------------------------------------------------------------
if "Notes" not in sys.modules:
    _notes_pkg = types.ModuleType("Notes")
    _notes_pkg.__path__ = [_NOTES_ROOT]
    _notes_pkg.__package__ = "Notes"
    sys.modules["Notes"] = _notes_pkg

# ---------------------------------------------------------------------------
# 5. Eagerly import app submodules
# ---------------------------------------------------------------------------
_SUBMODULES = [
    "db",
    "models",
    "schemas",
    "main",
    "services.embedding_service",
    "services.extract_service",
    "services.gemini_service",
    "services.file_service",
    "services.gcs_service",
    "services.session_memory",
    "utils.logging",
    "utils.auth",
    "routes.notebooks",
    "routes.sources",
    "routes.embeddings",
    "routes.chat",
]

for _submod in _SUBMODULES:
    try:
        importlib.import_module(_submod)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 6. Alias Notes.x <-> x
# ---------------------------------------------------------------------------
_ALIASES = [
    ("db", "Notes.db"),
    ("models", "Notes.models"),
    ("schemas", "Notes.schemas"),
    ("main", "Notes.main"),
    ("services", "Notes.services"),
    ("services.embedding_service", "Notes.services.embedding_service"),
    ("services.extract_service", "Notes.services.extract_service"),
    ("services.gemini_service", "Notes.services.gemini_service"),
    ("services.file_service", "Notes.services.file_service"),
    ("services.gcs_service", "Notes.services.gcs_service"),
    ("services.session_memory", "Notes.services.session_memory"),
    ("utils", "Notes.utils"),
    ("utils.logging", "Notes.utils.logging"),
    ("utils.auth", "Notes.utils.auth"),
    ("routes", "Notes.routes"),
    ("routes.notebooks", "Notes.routes.notebooks"),
    ("routes.sources", "Notes.routes.sources"),
    ("routes.embeddings", "Notes.routes.embeddings"),
    ("routes.chat", "Notes.routes.chat"),
]

for _bare, _prefixed in _ALIASES:
    _mod = sys.modules.get(_bare)
    if _mod is not None:
        sys.modules.setdefault(_prefixed, _mod)
    _mod2 = sys.modules.get(_prefixed)
    if _mod2 is not None:
        sys.modules.setdefault(_bare, _mod2)
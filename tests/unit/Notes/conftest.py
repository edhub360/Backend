"""
conftest.py for tests/unit/Notes/

Two problems this file solves:
1. sys.path — test files use BOTH bare imports (`from db import ...`) AND
   package-prefixed imports (`from Notes.db import ...`).  Both work only when:
     a) The Notes app root is in sys.path  →  bare `from db import ...` works
     b) The repo root is in sys.path       →  `from Notes.db import ...` works
   We add both here so no test file needs to be touched.

2. SQLite test engine — any test that imports the real `db` module at module
   level will trigger create_async_engine with PostgreSQL pool kwargs
   (pool_size, max_overflow, pool_timeout) that SQLite's StaticPool rejects.
   We patch create_async_engine before `db` is imported so the kwargs are
   silently accepted.
"""

import sys
import os
import importlib
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# ---------------------------------------------------------------------------
# 1.  Resolve paths
# ---------------------------------------------------------------------------
# Expected layout:
#   <repo_root>/
#       Notes/               ← Notes app root (contains db.py, models.py, etc.)
#           services/
#           routes/
#           utils/
#           schemas.py
#           main.py
#           ...
#       tests/
#           unit/
#               Notes/       ← this conftest lives here
#                   conftest.py

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))           # tests/unit/Notes
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "../../.."))  # repo root
_NOTES_ROOT = os.path.join(_REPO_ROOT, "Notes")                  # Notes app root

for _p in (_NOTES_ROOT, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# 2.  Stub heavy / unavailable third-party modules before any app code loads
# ---------------------------------------------------------------------------

def _stub(name: str, **attrs):
    """Insert a MagicMock for `name` and all missing parent packages."""
    parts = name.split(".")
    for i in range(1, len(parts) + 1):
        key = ".".join(parts[:i])
        if key not in sys.modules:
            sys.modules[key] = MagicMock()
    mod = sys.modules[name]
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod

# PyMuPDF (fitz) — PDF extraction
_stub("fitz")

# pgvector — vector column type
_pgvector = _stub("pgvector")
_pgvector_sa = _stub("pgvector.sqlalchemy")
_pgvector_sa.Vector = lambda dim=768: MagicMock()

# google-generativeai
_stub("google")
_stub("google.generativeai")

# youtube_transcript_api
_stub("youtube_transcript_api")

# python-docx
_stub("docx")

# python-pptx
_stub("pptx")

# openpyxl
_stub("openpyxl")

# google-cloud-storage
_stub("google.cloud")
_stub("google.cloud.storage")

# ---------------------------------------------------------------------------
# 3.  Patch create_async_engine so PostgreSQL-only pool kwargs don't blow up
#     when SQLite + StaticPool is used in tests that reload `db`.
# ---------------------------------------------------------------------------
# We wrap the real function and strip unsupported kwargs when the URL is SQLite.

try:
    from sqlalchemy.ext.asyncio import create_async_engine as _real_cae

    def _safe_create_async_engine(url, **kwargs):
        url_str = str(url)
        if "sqlite" in url_str:
            # SQLite + StaticPool does not accept these kwargs
            for key in ("pool_size", "max_overflow", "pool_timeout",
                        "pool_recycle", "pool_pre_ping"):
                kwargs.pop(key, None)
        return _real_cae(url, **kwargs)

    # Patch it into the db module's namespace after db is imported
    import sqlalchemy.ext.asyncio as _sa_async
    _sa_async.create_async_engine = _safe_create_async_engine

except ImportError:
    pass  # SQLAlchemy not installed — tests that need it will fail naturally


# ---------------------------------------------------------------------------
# 4.  Ensure Notes is a proper package (add __init__ if missing)
#     so `from Notes.x import y` works without an __init__.py on disk
# ---------------------------------------------------------------------------
import types as _types

if "Notes" not in sys.modules:
    _notes_pkg = _types.ModuleType("Notes")
    _notes_pkg.__path__ = [_NOTES_ROOT]
    _notes_pkg.__package__ = "Notes"
    sys.modules["Notes"] = _notes_pkg
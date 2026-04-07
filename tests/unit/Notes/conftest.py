"""
conftest.py  —  tests/unit/Notes/
"""

import sys
import os
import types
import importlib
from unittest.mock import MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# 1.  sys.path  — must be at MODULE LEVEL (before pytest_configure)
#     pytest needs the paths set before it even calls pytest_configure so
#     it can discover test files. Keep this as bare top-level code.
# ─────────────────────────────────────────────────────────────────────────────
_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT  = os.path.abspath(os.path.join(_THIS_DIR, "../../.."))
_NOTES_ROOT = os.path.join(_REPO_ROOT, "Notes")

for _p in (_NOTES_ROOT, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ─────────────────────────────────────────────────────────────────────────────
# Helper — defined at module level so pytest_configure can call it
# ─────────────────────────────────────────────────────────────────────────────
def _stub(name: str, **attrs):
    """Register a MagicMock for `name` and every missing parent package."""
    parts = name.split(".")
    for i in range(1, len(parts) + 1):
        key = ".".join(parts[:i])
        if key not in sys.modules:
            sys.modules[key] = MagicMock()
    mod = sys.modules[name]
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# 2-6.  Everything else lives inside pytest_configure
#       This hook fires BEFORE any test module is collected or imported,
#       which is exactly what we need for stubs, shims, and aliases.
# ─────────────────────────────────────────────────────────────────────────────
def pytest_configure(config):                          # ← ADD HERE

    # ── 2. Third-party stubs ─────────────────────────────────────────────────

    # PyMuPDF
    _stub("fitz")

    # pgvector
    _pgvector_sa = _stub("pgvector.sqlalchemy")
    _pgvector_sa.Vector = lambda dim=768: MagicMock()

    # asyncpg
    _stub("asyncpg")

    # beautifulsoup4
    _bs4 = _stub("bs4")
    _bs4.BeautifulSoup = MagicMock()

    # requests — real Exception subclasses so except-clauses don't TypeError
    _requests_mod = _stub("requests")

    class _RequestException(Exception): pass
    class _ConnectionError(_RequestException): pass
    class _Timeout(_RequestException): pass
    class _HTTPError(_RequestException): pass

    _req_exc = types.ModuleType("requests.exceptions")
    _req_exc.RequestException = _RequestException
    _req_exc.ConnectionError  = _ConnectionError
    _req_exc.Timeout          = _Timeout
    _req_exc.HTTPError        = _HTTPError
    sys.modules["requests.exceptions"] = _req_exc
    _requests_mod.exceptions = _req_exc

    # youtube_transcript_api
    _stub("youtube_transcript_api")

    # python-docx / python-pptx / openpyxl
    _stub("docx")
    _stub("pptx")
    _stub("openpyxl")

    # google-cloud-storage
    _stub("google.cloud.storage")

    # ⚠️  google.generativeai NOT stubbed here —
    #    test_gemini_services.py patches "services.gemini_service.genai"
    #    via autouse fixture; a conftest stub would shadow that patch target.

    # ── 3. create_async_engine shim ──────────────────────────────────────────
    try:
        from sqlalchemy.ext.asyncio import create_async_engine as _real_cae
        import sqlalchemy.ext.asyncio as _sa_async

        _PG_POOL_KWARGS = frozenset([
            "pool_size", "max_overflow", "pool_timeout",
            "pool_recycle", "pool_pre_ping",
        ])

        def _safe_cae(url, **kw):
            if "sqlite" in str(url):
                for k in _PG_POOL_KWARGS:
                    kw.pop(k, None)
            return _real_cae(url, **kw)

        _sa_async.create_async_engine = _safe_cae
    except ImportError:
        pass

    # ── 4. Notes package skeleton ────────────────────────────────────────────
    if "Notes" not in sys.modules:
        _notes_pkg = types.ModuleType("Notes")
        _notes_pkg.__path__    = [_NOTES_ROOT]
        _notes_pkg.__package__ = "Notes"
        sys.modules["Notes"]   = _notes_pkg

    # ── 5. Module aliases (BEFORE eager imports) ─────────────────────────────
    _ALIAS_PAIRS = [
        ("db",                         "Notes.db"),
        ("models",                     "Notes.models"),
        ("schemas",                    "Notes.schemas"),
        ("main",                       "Notes.main"),
        ("services",                   "Notes.services"),
        ("services.embedding_service", "Notes.services.embedding_service"),
        ("services.extract_service",   "Notes.services.extract_service"),
        ("services.gemini_service",    "Notes.services.gemini_service"),
        ("services.file_service",      "Notes.services.file_service"),
        ("services.gcs_service",       "Notes.services.gcs_service"),
        ("services.session_memory",    "Notes.services.session_memory"),
        ("utils",                      "Notes.utils"),
        ("utils.logging",              "Notes.utils.logging"),
        ("utils.auth",                 "Notes.utils.auth"),
        ("routes",                     "Notes.routes"),
        ("routes.notebooks",           "Notes.routes.notebooks"),
        ("routes.sources",             "Notes.routes.sources"),
        ("routes.embeddings",          "Notes.routes.embeddings"),
        ("routes.chat",                "Notes.routes.chat"),
    ]

    def _sync_aliases():
        for bare, prefixed in _ALIAS_PAIRS:
            a = sys.modules.get(bare)
            b = sys.modules.get(prefixed)
            if a is not None and b is None:
                sys.modules[prefixed] = a
            elif b is not None and a is None:
                sys.modules[bare] = b

    # Install meta-path finder that keeps aliases in sync on every import
    class _AliasFinder:
        def find_module(self, fullname, path=None):
            return None

        def find_spec(self, fullname, path, target=None):
            _sync_aliases()
            return None

    sys.meta_path.append(_AliasFinder())
    _sync_aliases()

    # ── 6. Eager submodule imports ────────────────────────────────────────────
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
            pass  # real errors surface in individual tests

    _sync_aliases()  # final sync after all eager imports
# tests/unit/notes/test_main.py

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ══════════════════════════════════════════════════════════════════════════════
# App fixture — patch all heavy dependencies before importing main
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def client():
    with patch("utils.logging.setup_logging"), \
         patch("routes.notebooks.router", MagicMock()), \
         patch("routes.sources.router", MagicMock()), \
         patch("routes.embeddings.router", MagicMock()), \
         patch("routes.chat.router", MagicMock()):
        import importlib
        import main as main_module
        importlib.reload(main_module)
        yield TestClient(main_module.app)


# ══════════════════════════════════════════════════════════════════════════════
# App metadata
# ══════════════════════════════════════════════════════════════════════════════
class TestAppMetadata:

    def test_app_title(self):
        with patch("utils.logging.setup_logging"), \
             patch("routes.notebooks.router", MagicMock()), \
             patch("routes.sources.router", MagicMock()), \
             patch("routes.embeddings.router", MagicMock()), \
             patch("routes.chat.router", MagicMock()):
            import importlib, main
            importlib.reload(main)
            assert main.app.title == "NotebookLM Backend"

    def test_app_version(self):
        with patch("utils.logging.setup_logging"), \
             patch("routes.notebooks.router", MagicMock()), \
             patch("routes.sources.router", MagicMock()), \
             patch("routes.embeddings.router", MagicMock()), \
             patch("routes.chat.router", MagicMock()):
            import importlib, main
            importlib.reload(main)
            assert main.app.version == "1.0.0"


# ══════════════════════════════════════════════════════════════════════════════
# CORS middleware
# ══════════════════════════════════════════════════════════════════════════════
class TestCORSMiddleware:

    def test_cors_middleware_registered(self, client):
        from starlette.middleware.cors import CORSMiddleware
        from main import app
        middleware_types = [m.cls for m in app.user_middleware]
        assert CORSMiddleware in middleware_types

    def test_cors_allows_all_origins(self, client):
        response = client.options(
            "/health",
            headers={"Origin": "http://example.com", "Access-Control-Request-Method": "GET"},
        )
        origin = response.headers.get("access-control-allow-origin", "")
        assert origin in ("*", "http://example.com")

    def test_cors_allows_credentials(self):
        from main import app
        for m in app.user_middleware:
            from starlette.middleware.cors import CORSMiddleware
            if m.cls is CORSMiddleware:
                assert m.kwargs.get("allow_credentials") is True


# ══════════════════════════════════════════════════════════════════════════════
# Root endpoint  GET /
# ══════════════════════════════════════════════════════════════════════════════
class TestRootEndpoint:

    def test_root_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_root_returns_msg_key(self, client):
        data = client.get("/").json()
        assert "msg" in data

    def test_root_message_content(self, client):
        data = client.get("/").json()
        assert "NotebookLM" in data["msg"] or "running" in data["msg"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# Health endpoint  GET /health
# ══════════════════════════════════════════════════════════════════════════════
class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_returns_status_key(self, client):
        data = client.get("/health").json()
        assert "status" in data

    def test_health_status_is_healthy(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"


# ══════════════════════════════════════════════════════════════════════════════
# Router registration
# ══════════════════════════════════════════════════════════════════════════════
class TestRouterRegistration:

    def _get_prefixes(self):
        from main import app
        return [r.path for r in app.routes]

    def test_notebooks_prefix_registered(self):
        prefixes = self._get_prefixes()
        assert any("/api/notebooks" in p for p in prefixes)

    def test_sources_prefix_registered(self):
        prefixes = self._get_prefixes()
        assert any("/api/sources" in p for p in prefixes)

    def test_embeddings_prefix_registered(self):
        prefixes = self._get_prefixes()
        assert any("/api/embeddings" in p for p in prefixes)

    def test_chat_prefix_registered(self):
        prefixes = self._get_prefixes()
        assert any("/api" in p for p in prefixes)

    def test_setup_logging_called_once(self):
        mock_setup = MagicMock()
        with patch("utils.logging.setup_logging", mock_setup), \
             patch("routes.notebooks.router", MagicMock()), \
             patch("routes.sources.router", MagicMock()), \
             patch("routes.embeddings.router", MagicMock()), \
             patch("routes.chat.router", MagicMock()):
            import importlib, main
            importlib.reload(main)
            mock_setup.assert_called_once_with(main.app)


# ══════════════════════════════════════════════════════════════════════════════
# Unknown routes
# ══════════════════════════════════════════════════════════════════════════════
class TestUnknownRoutes:

    def test_unknown_route_returns_404(self, client):
        assert client.get("/does-not-exist").status_code == 404

    def test_root_does_not_accept_post(self, client):
        assert client.post("/").status_code == 405

    def test_health_does_not_accept_post(self, client):
        assert client.post("/health").status_code == 405
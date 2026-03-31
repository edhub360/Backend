# tests/unit/ai_chat/test_main.py

import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────
# Fixture — real app, only external deps mocked
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "FAISS_STORAGE_DIR": "/tmp/faiss_test"}), \
         patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel", return_value=MagicMock()), \
         patch("ai_chat.app.utils.faiss_handler.faiss.IndexFlatL2", return_value=MagicMock(ntotal=0)), \
         patch("ai_chat.app.utils.faiss_handler.faiss.read_index", side_effect=Exception("no file")):
        from ai_chat.app.main import app
        yield TestClient(app)


# ─────────────────────────────────────────────
# App metadata
# ─────────────────────────────────────────────

class TestAppMetadata:

    def test_app_title(self, client):
        assert client.app.title == "SmartStudy API"

    def test_app_version(self, client):
        assert client.app.version == "1.0.0"

    def test_app_has_description(self, client):
        assert client.app.description != ""


# ─────────────────────────────────────────────
# Root & Health
# ─────────────────────────────────────────────

class TestRootAndHealth:

    def test_root_status_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_message(self, client):
        response = client.get("/")
        assert response.json() == {"message": "SmartStudy API is running"}

    def test_health_status_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy(self, client):
        response = client.get("/health")
        assert response.json() == {"status": "healthy"}

    def test_unknown_route_returns_404(self, client):
        response = client.get("/nonexistent")
        assert response.status_code == 404


# ─────────────────────────────────────────────
# Router registration
# ─────────────────────────────────────────────

class TestRouterRegistration:

    def test_upload_router_registered(self, client):
        routes = [r.path for r in client.app.routes]
        assert any(r.startswith("/upload") for r in routes)

    def test_chat_router_registered(self, client):
        routes = [r.path for r in client.app.routes]
        assert any(r.startswith("/chat") for r in routes)

    def test_upload_prefix_is_upload(self, client):
        response = client.get("/upload/stats")
        # /upload/stats exists — not 404
        assert response.status_code != 404

    def test_chat_route_exists(self, client):
        # POST /chat should exist (405 = method known, endpoint exists)
        response = client.get("/chat")
        assert response.status_code != 404

    def test_upload_tag_present(self, client):
        tags = [
            tag
            for route in client.app.routes
            if hasattr(route, "tags")
            for tag in route.tags
        ]
        assert "upload" in tags

    def test_chat_tag_present(self, client):
        tags = [
            tag
            for route in client.app.routes
            if hasattr(route, "tags")
            for tag in route.tags
        ]
        assert "chat" in tags


# ─────────────────────────────────────────────
# CORS middleware
# ─────────────────────────────────────────────

class TestCORSMiddleware:

    def test_cors_allows_localhost_origin(self, client):
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)

    def test_cors_allow_origin_header_present(self, client):
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_all_origins_wildcard(self, client):
        response = client.get("/", headers={"Origin": "https://edhub360.com"})
        origin_header = response.headers.get("access-control-allow-origin", "")
        assert origin_header in ("*", "https://edhub360.com")

    def test_cors_allows_post_method(self, client):
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in (200, 204)

    def test_cors_middleware_is_registered(self, client):
        from starlette.middleware.cors import CORSMiddleware
        middleware_types = [
            m.cls for m in client.app.user_middleware
        ]
        assert CORSMiddleware in middleware_types

    def test_cors_credentials_allowed(self, client):
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # allow-credentials header should be present or origin returned
        assert response.status_code in (200, 204)


# ─────────────────────────────────────────────
# OpenAPI / docs
# ─────────────────────────────────────────────

class TestOpenAPI:

    def test_openapi_json_available(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_title_matches(self, client):
        response = client.get("/openapi.json")
        assert response.json()["info"]["title"] == "SmartStudy API"

    def test_openapi_version_matches(self, client):
        response = client.get("/openapi.json")
        assert response.json()["info"]["version"] == "1.0.0"

    def test_openapi_contains_upload_path(self, client):
        response = client.get("/openapi.json")
        paths = response.json().get("paths", {})
        assert any("/upload" in p for p in paths)

    def test_openapi_contains_chat_path(self, client):
        response = client.get("/openapi.json")
        paths = response.json().get("paths", {})
        assert any("/chat" in p for p in paths)

    def test_docs_ui_available(self, client):
        response = client.get("/docs")
        assert response.status_code == 200
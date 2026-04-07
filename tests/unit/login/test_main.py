"""
tests/unit/login/test_main.py
================================
Unit tests for app/main.py

Coverage:
  - GET /          — root health check
  - GET /health    — health endpoint
  - CORS middleware registered
  - Rate limiter attached to app state
  - Global exception handler returns 500 with generic message
  - Both routers are mounted (auth + password_reset)
  - docs/redoc URLs controlled by debug flag
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from login.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ══════════════════════════════════════════════════════════════════════════════
# GET /  — root
# ══════════════════════════════════════════════════════════════════════════════
class TestRootEndpoint:

    def test_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_returns_status_healthy(self, client):
        assert client.get("/").json()["status"] == "healthy"

    def test_returns_version(self, client):
        data = client.get("/").json()
        assert "version" in data

    def test_returns_message(self, client):
        data = client.get("/").json()
        assert "message" in data

    def test_message_mentions_auth(self, client):
        data = client.get("/").json()
        assert "Auth" in data["message"] or "auth" in data["message"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# GET /health
# ══════════════════════════════════════════════════════════════════════════════
class TestHealthEndpoint:

    def test_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_returns_status_healthy(self, client):
        assert client.get("/health").json()["status"] == "healthy"

    def test_returns_service_name(self, client):
        data = client.get("/health").json()
        assert "service" in data


# ══════════════════════════════════════════════════════════════════════════════
# CORS middleware
# ══════════════════════════════════════════════════════════════════════════════
class TestCORSMiddleware:

    def test_cors_header_present_for_allowed_origin(self, client):
        resp = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert "access-control-allow-origin" in resp.headers

    def test_options_preflight_returns_200(self, client):
        resp = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert resp.status_code in (200, 204)


# ══════════════════════════════════════════════════════════════════════════════
# Rate limiter
# ══════════════════════════════════════════════════════════════════════════════
class TestRateLimiter:

    def test_limiter_attached_to_app_state(self):
        from login.app.main import app
        assert hasattr(app.state, "limiter")

    def test_limiter_is_not_none(self):
        from login.app.main import app
        assert app.state.limiter is not None


# ══════════════════════════════════════════════════════════════════════════════
# Global exception handler
# ══════════════════════════════════════════════════════════════════════════════
class TestGlobalExceptionHandler:

    def test_unhandled_exception_returns_500(self):
        from login.app.main import app
        from fastapi.testclient import TestClient

        @app.get("/test-crash")
        async def crash():
            raise RuntimeError("Simulated internal error")

        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/test-crash")
        assert resp.status_code == 500

    def test_unhandled_exception_returns_generic_message(self):
        from login.app.main import app
        from fastapi.testclient import TestClient

        @app.get("/test-crash-2")
        async def crash2():
            raise ValueError("Sensitive data should not leak")

        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/test-crash-2")
        body = resp.json()
        assert "detail" in body
        assert "Sensitive data" not in body["detail"]
        assert body["detail"] == "Internal server error"


# ══════════════════════════════════════════════════════════════════════════════
# Router mounting
# ══════════════════════════════════════════════════════════════════════════════
class TestRouterMounting:

    def test_auth_routes_are_mounted(self):
        from login.app.main import app
        paths = [r.path for r in app.routes]
        assert any("/auth" in p for p in paths)

    def test_auth_register_route_reachable(self, client):
        # POST with empty body → 422 (validation), not 404
        resp = client.post("/auth/register", json={})
        assert resp.status_code != 404

    def test_auth_login_route_reachable(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code != 404

    def test_forgot_password_route_reachable(self, client):
        resp = client.post("/auth/forgot-password", json={})
        assert resp.status_code != 404

    def test_reset_password_route_reachable(self, client):
        resp = client.post("/auth/reset-password", json={})
        assert resp.status_code != 404

    def test_health_route_exists(self, client):
        assert client.get("/health").status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# App metadata
# ══════════════════════════════════════════════════════════════════════════════
class TestAppMetadata:

    def test_app_title_set(self):
        from login.app.main import app
        assert app.title is not None and len(app.title) > 0

    def test_app_version_is_1_0_0(self):
        from login.app.main import app
        assert app.version == "1.0.0"

    def test_docs_hidden_when_debug_false(self):
        """When debug=False, /docs should return 404."""
        from login.app.config import settings
        if not settings.debug:
            from login.app.main import app
            c = TestClient(app, raise_server_exceptions=False)
            assert c.get("/docs").status_code == 404

    def test_redoc_hidden_when_debug_false(self):
        from login.app.config import settings
        if not settings.debug:
            from login.app.main import app
            c = TestClient(app, raise_server_exceptions=False)
            assert c.get("/redoc").status_code == 404
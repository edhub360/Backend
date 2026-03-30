"""
tests/unit/ai_chat/test_main.py
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("app.routes.upload.router"), \
         patch("app.routes.chat.router"):
        from ai_chat.app.main import app
        return TestClient(app)


class TestAIChatMain:

    def test_root_returns_running_message(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "SmartStudy API is running"}

    def test_health_check_returns_healthy(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_cors_allows_all_origins(self, client):
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert response.status_code in (200, 204)

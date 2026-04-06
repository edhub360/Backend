import pytest


@pytest.fixture
def mock_settings():
    return {
        "jwt_secret_key": "fake-jwt-secret-for-testing",
        "jwt_algorithm": "HS256",
        "access_token_expire_minutes": 15,
        "google_client_id": "fake-google-client-id",
    }


@pytest.fixture
def mock_google_verify(monkeypatch):
    async def mock_verify(*args, **kwargs):
        return {
            "google_id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
        }
    monkeypatch.setattr("login.app.auth.verify_google_token", mock_verify)


@pytest.fixture
def sample_user_data():
    return {
        "email": "test@example.com",
        "name": "Test User",
        "language": "en",
        "subscription_tier": "free",
    }
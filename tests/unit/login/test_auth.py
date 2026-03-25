import pytest
import sys
from unittest.mock import MagicMock

# Mock entire 'app' package and all its submodules
_app_mock = MagicMock()
sys.modules["app"] = _app_mock
sys.modules["app.config"] = MagicMock(settings=MagicMock(
    jwt_secret_key="test-secret-key-do-not-use-in-production-abc123",
    jwt_algorithm="HS256",
    access_token_expire_minutes=15,
    google_client_id="fake-google-client-id",
    google_client_secret="fake-google-client-secret",
    refresh_token_expire_days=7,
))
sys.modules["app.utils"] = MagicMock(
    generate_secure_token=MagicMock(return_value="fake-token-abc123"),
    hash_token=MagicMock(return_value="fake-hashed-token"),
)

from login.app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing functions"""

    def test_hash_password(self):
        password = "secure_password_123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > len(password)

    def test_verify_password_correct(self):
        password = "secure_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "secure_password_123"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False

    def test_bcrypt_72_byte_limit(self):
        long_password = "a" * 100
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) is True


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and verification"""

    def test_create_access_token(self):
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)
        decoded = decode_jwt_token(token)
        assert decoded["sub"] == "user@example.com"
        assert decoded["user_id"] == "123"

    def test_decode_expired_token(self):
        from freezegun import freeze_time
        data = {"sub": "user@example.com"}
        token = create_access_token(data)
        with freeze_time("2099-01-01"):
            with pytest.raises(Exception):
                decode_jwt_token(token)

    def test_create_refresh_token(self):
        token, token_hash = create_refresh_token()
        assert isinstance(token, str)
        assert isinstance(token_hash, str)
        assert token != token_hash
        assert len(token) > 0

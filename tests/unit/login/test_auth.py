import pytest
import sys
from unittest.mock import MagicMock

# --- Mock 'app.config' before importing login.app.auth ---
# login/app/auth.py does "from app.config import settings"
# which requires login/ to be treated as the root.
# We mock it here to avoid ModuleNotFoundError in CI.
mock_settings = MagicMock()
mock_settings.jwt_secret_key = "test-secret-key-do-not-use-in-production"
mock_settings.jwt_algorithm = "HS256"
mock_settings.access_token_expire_minutes = 15

sys.modules.setdefault("app", MagicMock())
sys.modules.setdefault("app.config", MagicMock(settings=mock_settings))

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

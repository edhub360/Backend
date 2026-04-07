"""
tests/unit/login/test_auth_utils.py
Unit tests for app/auth.py core utilities
"""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt


class TestHashPassword:
    def test_returns_string(self):
        from login.app.auth import hash_password
        assert isinstance(hash_password("Secure123"), str)

    def test_not_equal_to_plaintext(self):
        from login.app.auth import hash_password
        assert hash_password("Secure123") != "Secure123"

    def test_different_passwords_different_hashes(self):
        from login.app.auth import hash_password
        assert hash_password("PasswordA1") != hash_password("PasswordB2")

    def test_same_password_different_hashes_each_time(self):
        """bcrypt uses unique salt on every call."""
        from login.app.auth import hash_password
        assert hash_password("Same1Password") != hash_password("Same1Password")

    def test_bcrypt_prefix_in_hash(self):
        from login.app.auth import hash_password
        assert hash_password("Secure123").startswith("$2b$")

    def test_truncates_at_72_bytes(self):
        from login.app.auth import hash_password
        assert hash_password("A" * 100).startswith("$2b$")


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        from login.app.auth import hash_password, verify_password
        h = hash_password("Secure123")
        assert verify_password("Secure123", h) is True

    def test_wrong_password_returns_false(self):
        from login.app.auth import hash_password, verify_password
        h = hash_password("Secure123")
        assert verify_password("WrongPass1", h) is False

    def test_empty_input_returns_false(self):
        from login.app.auth import hash_password, verify_password
        h = hash_password("Secure123")
        assert verify_password("", h) is False

    def test_case_sensitive(self):
        from login.app.auth import hash_password, verify_password
        h = hash_password("Secure123")
        assert verify_password("secure123", h) is False


class TestCreateAccessToken:
    def test_returns_string(self):
        from login.app.auth import create_access_token
        assert isinstance(create_access_token({"sub": "u1"}), str)

    def test_contains_three_parts(self):
        from login.app.auth import create_access_token
        assert len(create_access_token({"sub": "u1"}).split(".")) == 3

    def test_payload_sub_matches(self):
        from login.app.auth import create_access_token, decode_jwt_token
        token = create_access_token({"sub": "user-id-abc"})
        assert decode_jwt_token(token)["sub"] == "user-id-abc"

    def test_payload_email_matches(self):
        from login.app.auth import create_access_token, decode_jwt_token
        token = create_access_token({"sub": "u1", "email": "x@y.com"})
        assert decode_jwt_token(token)["email"] == "x@y.com"

    def test_token_has_exp_claim(self):
        from login.app.auth import create_access_token, decode_jwt_token
        assert "exp" in decode_jwt_token(create_access_token({"sub": "u1"}))

    def test_token_has_iat_claim(self):
        from login.app.auth import create_access_token, decode_jwt_token
        assert "iat" in decode_jwt_token(create_access_token({"sub": "u1"}))

    def test_exp_is_in_the_future(self):
        from login.app.auth import create_access_token, decode_jwt_token
        payload = decode_jwt_token(create_access_token({"sub": "u1"}))
        assert payload["exp"] > datetime.now(timezone.utc).timestamp()


class TestCreateRefreshToken:
    def test_returns_tuple_of_two(self):
        from login.app.auth import create_refresh_token
        result = create_refresh_token()
        assert isinstance(result, tuple) and len(result) == 2

    def test_token_and_hash_differ(self):
        from login.app.auth import create_refresh_token
        token, token_hash = create_refresh_token()
        assert token != token_hash

    def test_each_call_returns_unique_token(self):
        from login.app.auth import create_refresh_token
        t1, _ = create_refresh_token()
        t2, _ = create_refresh_token()
        assert t1 != t2

    def test_hash_is_deterministic(self):
        from login.app.utils import hash_token
        t = "some-fixed-token"
        assert hash_token(t) == hash_token(t)


class TestDecodeJwtToken:
    def test_decodes_valid_token(self):
        from login.app.auth import create_access_token, decode_jwt_token
        token = create_access_token({"sub": "u1"})
        assert decode_jwt_token(token)["sub"] == "u1"

    def test_raises_401_for_invalid_token(self):
        from login.app.auth import decode_jwt_token
        with pytest.raises(HTTPException) as exc:
            decode_jwt_token("totally.invalid.token")
        assert exc.value.status_code == 401

    def test_raises_401_for_tampered_token(self):
        from login.app.auth import create_access_token, decode_jwt_token
        token = create_access_token({"sub": "u1"})
        with pytest.raises(HTTPException) as exc:
            decode_jwt_token(token[:-5] + "XXXXX")
        assert exc.value.status_code == 401

    def test_raises_401_for_expired_token(self):
        from login.app.auth import decode_jwt_token
        from login.app.config import settings
        payload = {
            "sub": "u1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        with pytest.raises(HTTPException) as exc:
            decode_jwt_token(token)
        assert exc.value.status_code == 401

    def test_raises_401_for_empty_string(self):
        from login.app.auth import decode_jwt_token
        with pytest.raises(HTTPException) as exc:
            decode_jwt_token("")
        assert exc.value.status_code == 401
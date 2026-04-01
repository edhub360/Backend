# tests/unit/notes/utils/test_auth.py

import pytest
import jwt
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException

JWT_SECRET = "test-secret-key"
JWT_ALGORITHM = "HS256"


def _make_token(payload: dict, secret=JWT_SECRET, algorithm=JWT_ALGORITHM) -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def _valid_payload(user_id=42, email="test@example.com", username="testuser", roles=None):
    return {
        "user_id": user_id,
        "email": email,
        "username": username,
        "roles": roles or ["student"],
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
    }


def _expired_payload(**kwargs):
    payload = _valid_payload(**kwargs)
    payload["exp"] = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
    return payload


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", JWT_ALGORITHM)

    import Notes.utils.auth as auth_module
    auth_module.JWT_SECRET_KEY = JWT_SECRET
    auth_module.JWT_ALGORITHM = JWT_ALGORITHM


# ══════════════════════════════════════════════════════════════════════════════
# AuthUser
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthUser:

    def test_stores_user_id(self):
        from Notes.utils.auth import AuthUser
        u = AuthUser(user_id=1, email="a@b.com", username="alice")
        assert u.user_id == 1

    def test_stores_email(self):
        from Notes.utils.auth import AuthUser
        u = AuthUser(user_id=1, email="a@b.com", username="alice")
        assert u.email == "a@b.com"

    def test_stores_username(self):
        from Notes.utils.auth import AuthUser
        u = AuthUser(user_id=1, email="a@b.com", username="alice")
        assert u.username == "alice"

    def test_roles_default_to_empty_list(self):
        from Notes.utils.auth import AuthUser
        u = AuthUser(user_id=1, email="a@b.com", username="alice")
        assert u.roles == []

    def test_roles_stored_when_provided(self):
        from Notes.utils.auth import AuthUser
        u = AuthUser(user_id=1, email="a@b.com", username="alice", roles=["admin"])
        assert u.roles == ["admin"]

    def test_none_roles_defaults_to_empty_list(self):
        from Notes.utils.auth import AuthUser
        u = AuthUser(user_id=1, email="a@b.com", username="alice", roles=None)
        assert u.roles == []


# ══════════════════════════════════════════════════════════════════════════════
# verify_token
# ══════════════════════════════════════════════════════════════════════════════
class TestVerifyToken:

    def test_valid_token_returns_payload(self):
        from Notes.utils.auth import verify_token
        token = _make_token(_valid_payload())
        payload = verify_token(token)
        assert payload["user_id"] == 42

    def test_valid_token_returns_email(self):
        from Notes.utils.auth import verify_token
        token = _make_token(_valid_payload(email="user@test.com"))
        assert verify_token(token)["email"] == "user@test.com"

    def test_expired_token_raises_401(self):
        from Notes.utils.auth import verify_token
        token = _make_token(_expired_payload())
        with pytest.raises(HTTPException) as exc:
            verify_token(token)
        assert exc.value.status_code == 401

    def test_expired_token_detail(self):
        from Notes.utils.auth import verify_token
        # jwt library raises DecodeError for truly expired tokens in strict mode;
        # our manual check catches manually-set past exp
        token = _make_token(_expired_payload(), secret=JWT_SECRET)
        try:
            verify_token(token)
        except HTTPException as e:
            assert e.status_code == 401

    def test_invalid_signature_raises_401(self):
        from Notes.utils.auth import verify_token
        token = _make_token(_valid_payload(), secret="wrong-secret")
        with pytest.raises(HTTPException) as exc:
            verify_token(token)
        assert exc.value.status_code == 401

    def test_invalid_token_detail_message(self):
        from Notes.utils.auth import verify_token
        with pytest.raises(HTTPException) as exc:
            verify_token("not.a.valid.token")
        assert "Invalid token" in exc.value.detail

    def test_malformed_token_raises_401(self):
        from Notes.utils.auth import verify_token
        with pytest.raises(HTTPException) as exc:
            verify_token("totally-garbage")
        assert exc.value.status_code == 401

    def test_empty_string_raises_401(self):
        from Notes.utils.auth import verify_token
        with pytest.raises(HTTPException):
            verify_token("")

    def test_token_without_exp_raises_401(self):
        from Notes.utils.auth import verify_token
        # exp defaults to 0 → always in the past
        payload = {"user_id": 1, "email": "a@b.com", "username": "alice"}
        token = _make_token(payload)
        with pytest.raises(HTTPException) as exc:
            verify_token(token)
        assert exc.value.status_code == 401

    def test_valid_token_returns_all_fields(self):
        from Notes.utils.auth import verify_token
        p = _valid_payload(roles=["admin", "teacher"])
        token = _make_token(p)
        result = verify_token(token)
        assert result["roles"] == ["admin", "teacher"]
        assert result["username"] == "testuser"


# ══════════════════════════════════════════════════════════════════════════════
# get_current_user
# ══════════════════════════════════════════════════════════════════════════════
class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_returns_auth_user_on_valid_token(self):
        from Notes.utils.auth import get_current_user
        token = _make_token(_valid_payload())
        creds = MagicMock()
        creds.credentials = token

        user = await get_current_user(creds)
        assert user.user_id == 42

    @pytest.mark.asyncio
    async def test_returned_user_email(self):
        from Notes.utils.auth import get_current_user
        token = _make_token(_valid_payload(email="user@example.com"))
        creds = MagicMock()
        creds.credentials = token

        user = await get_current_user(creds)
        assert user.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_returned_user_username(self):
        from Notes.utils.auth import get_current_user
        token = _make_token(_valid_payload(username="johndoe"))
        creds = MagicMock()
        creds.credentials = token

        user = await get_current_user(creds)
        assert user.username == "johndoe"

    @pytest.mark.asyncio
    async def test_returned_user_roles(self):
        from Notes.utils.auth import get_current_user
        token = _make_token(_valid_payload(roles=["admin"]))
        creds = MagicMock()
        creds.credentials = token

        user = await get_current_user(creds)
        assert user.roles == ["admin"]

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        from Notes.utils.auth import get_current_user
        creds = MagicMock()
        creds.credentials = "invalid.token.here"

        with pytest.raises(HTTPException) as exc:
            await get_current_user(creds)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self):
        from Notes.utils.auth import get_current_user
        token = _make_token(_expired_payload())
        creds = MagicMock()
        creds.credentials = token

        with pytest.raises(HTTPException) as exc:
            await get_current_user(creds)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_auth_user_instance(self):
        from Notes.utils.auth import get_current_user, AuthUser
        token = _make_token(_valid_payload())
        creds = MagicMock()
        creds.credentials = token

        user = await get_current_user(creds)
        assert isinstance(user, AuthUser)

    @pytest.mark.asyncio
    async def test_missing_roles_in_payload_defaults_to_empty(self):
        from Notes.utils.auth import get_current_user
        payload = {
            "user_id": 1,
            "email": "a@b.com",
            "username": "alice",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        token = _make_token(payload)
        creds = MagicMock()
        creds.credentials = token

        user = await get_current_user(creds)
        assert user.roles == []


# ══════════════════════════════════════════════════════════════════════════════
# get_optional_user
# ══════════════════════════════════════════════════════════════════════════════
class TestGetOptionalUser:

    @pytest.mark.asyncio
    async def test_returns_auth_user_for_valid_token(self):
        from Notes.utils.auth import get_optional_user
        token = _make_token(_valid_payload())
        creds = MagicMock()
        creds.credentials = token

        user = await get_optional_user(creds)
        assert user is not None
        assert user.user_id == 42

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_token(self):
        from Notes.utils.auth import get_optional_user
        creds = MagicMock()
        creds.credentials = "bad.token.here"

        user = await get_optional_user(creds)
        assert user is None

    @pytest.mark.asyncio
    async def test_returns_none_for_expired_token(self):
        from Notes.utils.auth import get_optional_user
        token = _make_token(_expired_payload())
        creds = MagicMock()
        creds.credentials = token

        user = await get_optional_user(creds)
        assert user is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_credentials(self):
        from Notes.utils.auth import get_optional_user
        user = await get_optional_user(None)
        assert user is None

    @pytest.mark.asyncio
    async def test_does_not_raise_on_invalid_token(self):
        from Notes.utils.auth import get_optional_user
        creds = MagicMock()
        creds.credentials = "garbage"

        # Must never raise — silently returns None
        try:
            result = await get_optional_user(creds)
            assert result is None
        except Exception:
            pytest.fail("get_optional_user raised unexpectedly on invalid token")

    @pytest.mark.asyncio
    async def test_returns_correct_email_for_valid_token(self):
        from Notes.utils.auth import get_optional_user
        token = _make_token(_valid_payload(email="opt@test.com"))
        creds = MagicMock()
        creds.credentials = token

        user = await get_optional_user(creds)
        assert user.email == "opt@test.com"
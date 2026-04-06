# tests/unit/ai_chat/test_auth.py

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

SECRET = "your-secret-key"
ALGORITHM = "HS256"

# ── NEW: force the correct secret in every test in this file ─────────────────
@pytest.fixture(autouse=True)
def patch_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.setattr("ai_chat.app.utils.auth.JWT_SECRET_KEY", SECRET)
# ─────────────────────────────────────────────────────────────────────────────

def make_token(
    user_id: int = 1,
    email: str = "user@example.com",
    username: str = "testuser",
    roles: list = None,
    exp_delta: int = 3600,  # seconds from now; negative = expired
) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "username": username,
        "roles": roles or ["student"],
        "exp": (datetime.now(timezone.utc) + timedelta(seconds=exp_delta)).timestamp(),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


# ─────────────────────────────────────────────
# AuthUser
# ─────────────────────────────────────────────

class TestAuthUser:

    def test_stores_all_fields(self):
        from ai_chat.app.utils.auth import AuthUser

        user = AuthUser(user_id=42, email="a@b.com", username="alice", roles=["admin"])
        assert user.user_id == 42
        assert user.email == "a@b.com"
        assert user.username == "alice"
        assert user.roles == ["admin"]

    def test_roles_defaults_to_empty_list(self):
        from ai_chat.app.utils.auth import AuthUser

        user = AuthUser(user_id=1, email="a@b.com", username="alice")
        assert user.roles == []

    def test_roles_none_becomes_empty_list(self):
        from ai_chat.app.utils.auth import AuthUser

        user = AuthUser(user_id=1, email="a@b.com", username="alice", roles=None)
        assert user.roles == []


# ─────────────────────────────────────────────
# verify_token
# ─────────────────────────────────────────────

class TestVerifyToken:

    def test_valid_token_returns_payload(self):
        from ai_chat.app.utils.auth import verify_token

        token = make_token()
        payload = verify_token(token)

        assert payload["user_id"] == 1
        assert payload["email"] == "user@example.com"
        assert payload["username"] == "testuser"

    def test_valid_token_includes_roles(self):
        from ai_chat.app.utils.auth import verify_token

        token = make_token(roles=["admin", "teacher"])
        payload = verify_token(token)

        assert payload["roles"] == ["admin", "teacher"]

    def test_expired_token_raises_401(self):
        from ai_chat.app.utils.auth import verify_token

        token = make_token(exp_delta=-10)  # expired 10s ago

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)

        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self):
        from ai_chat.app.utils.auth import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("this.is.not.a.jwt")

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    def test_wrong_secret_raises_401(self):
        from ai_chat.app.utils.auth import verify_token

        token = jwt.encode({"user_id": 1, "exp": 9999999999}, "wrong-secret", algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)

        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        from ai_chat.app.utils.auth import verify_token

        token = make_token()
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + "TAMPERED." + parts[2]

        with pytest.raises(HTTPException) as exc_info:
            verify_token(tampered)

        assert exc_info.value.status_code == 401

    def test_missing_exp_field_passes_jwt_decode(self):
        """Token without 'exp' field — jwt.decode won't enforce expiry, but our manual check uses get('exp', 0)."""
        from ai_chat.app.utils.auth import verify_token

        # No exp → payload.get("exp", 0) == 0 → already "expired" by our manual check
        token = jwt.encode({"user_id": 99, "email": "x@y.com", "username": "x"}, SECRET, algorithm=ALGORITHM)

        # This will hit the manual expiry check since exp=0 < utcnow()
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token expired"

    def test_empty_string_token_raises_401(self):
        from ai_chat.app.utils.auth import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("")

        assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────
# get_current_user
# ─────────────────────────────────────────────

class TestGetCurrentUser:

    @pytest.mark.anyio
    async def test_valid_credentials_returns_auth_user(self):
        from ai_chat.app.utils.auth import get_current_user

        token = make_token(user_id=7, email="dev@edhub.com", username="devuser", roles=["student"])
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user(credentials=creds)

        assert user.user_id == 7
        assert user.email == "dev@edhub.com"
        assert user.username == "devuser"
        assert user.roles == ["student"]

    @pytest.mark.anyio
    async def test_expired_token_raises_401(self):
        from ai_chat.app.utils.auth import get_current_user

        token = make_token(exp_delta=-60)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == 401

    @pytest.mark.anyio
    async def test_invalid_token_raises_401(self):
        from ai_chat.app.utils.auth import get_current_user

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == 401

    @pytest.mark.anyio
    async def test_roles_default_to_empty_list_when_missing_from_payload(self):
        from ai_chat.app.utils.auth import get_current_user

        # Token with no 'roles' key but a valid future exp
        payload = {
            "user_id": 5,
            "email": "noroles@test.com",
            "username": "noroles",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user(credentials=creds)

        assert user.roles == []

    @pytest.mark.anyio
    async def test_returns_auth_user_instance(self):
        from ai_chat.app.utils.auth import get_current_user, AuthUser

        token = make_token()
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user(credentials=creds)

        assert isinstance(user, AuthUser)

    @pytest.mark.anyio
    @patch("ai_chat.app.utils.auth.verify_token")
    async def test_get_current_user_calls_verify_token(self, mock_verify):
        from ai_chat.app.utils.auth import get_current_user

        mock_verify.return_value = {
            "user_id": 3,
            "email": "mock@test.com",
            "username": "mockuser",
            "roles": ["admin"],
        }
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="anytoken")

        user = await get_current_user(credentials=creds)

        mock_verify.assert_called_once_with("anytoken")
        assert user.user_id == 3
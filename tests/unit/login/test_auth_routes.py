"""
tests/unit/login/test_auth_routes.py
=====================================
Unit tests for app/routes/auth_routes.py

Coverage:
  - POST /auth/register
  - POST /auth/login
  - POST /auth/google
  - POST /auth/refresh
  - POST /auth/logout
  - GET  /auth/me
  - PATCH /auth/me
  - get_current_user dependency
  - Helper functions: get_user_by_email, create_user,
    create_auth_credential, create_refresh_token_db,
    generate_tokens, enforce_free_plan_expiry
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

USER_ID        = uuid4()
USER_EMAIL     = "test@example.com"
USER_NAME      = "Test User"
RAW_PASSWORD       = "Secure123"
HASHED_PASSWORD    = "$2b$12$fakehash"
ACCESS_TOKEN       = "fake.access.token"
REFRESH_TOKEN      = "fake-refresh-token"
REFRESH_TOKEN_HASH = "hashed-refresh-token"


def _make_user(
    user_id=None,
    email=USER_EMAIL,
    name=USER_NAME,
    subscription_tier=None,
    free_plan_expires_at=None,
):
    u = MagicMock()
    u.user_id               = user_id or USER_ID
    u.email                 = email
    u.name                  = name
    u.subscription_tier     = subscription_tier
    u.free_plan_expires_at  = free_plan_expires_at
    u.free_plan_activated_at = None
    u.language              = None
    u.created_at            = datetime.now(timezone.utc)
    return u


def _make_auth_cred(password_hash=HASHED_PASSWORD, provider="email"):
    c = MagicMock()
    c.password_hash = password_hash
    c.provider = provider
    return c


def _make_refresh_token_record(revoked=False, expired=False):
    rt = MagicMock()
    rt.user_id  = USER_ID
    rt.revoked  = revoked
    rt.expires_at = (
        datetime.now(timezone.utc) - timedelta(hours=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(days=7)
    )
    return rt


def _make_db_session():
    return AsyncMock()


def _result_returning(obj):
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    return result


def _make_app_with_db(mock_db):
    from login.app.routes.auth_routes import router
    from login.app.db import get_db
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    app = FastAPI()
    app.state.limiter = Limiter(key_func=get_remote_address)

    async def fake_db():
        yield mock_db

    app.dependency_overrides[get_db] = fake_db
    app.include_router(router)
    return app


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/register
# ══════════════════════════════════════════════════════════════════════════════
class TestRegister:

    PAYLOAD = {"email": USER_EMAIL, "password": "Secure123", "name": USER_NAME}

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = _make_db_session()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/auth/register"

    def _no_existing_user(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute = AsyncMock(return_value=result)

    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    @patch("login.app.routes.auth_routes.hash_password", return_value=HASHED_PASSWORD)
    def test_returns_200_on_success(self, mock_hash, mock_access, mock_refresh):
        self._no_existing_user()
        user = _make_user()
        with patch("login.app.routes.auth_routes.create_user", new=AsyncMock(return_value=user)), \
             patch("login.app.routes.auth_routes.create_auth_credential", new=AsyncMock()), \
             patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.status_code == 200

    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    @patch("login.app.routes.auth_routes.hash_password", return_value=HASHED_PASSWORD)
    def test_response_contains_access_token(self, mock_hash, mock_access, mock_refresh):
        self._no_existing_user()
        user = _make_user()
        with patch("login.app.routes.auth_routes.create_user", new=AsyncMock(return_value=user)), \
             patch("login.app.routes.auth_routes.create_auth_credential", new=AsyncMock()), \
             patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.json()["access_token"] == ACCESS_TOKEN

    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    @patch("login.app.routes.auth_routes.hash_password", return_value=HASHED_PASSWORD)
    def test_is_first_login_true_for_new_user(self, mock_hash, mock_access, mock_refresh):
        self._no_existing_user()
        user = _make_user()
        with patch("login.app.routes.auth_routes.create_user", new=AsyncMock(return_value=user)), \
             patch("login.app.routes.auth_routes.create_auth_credential", new=AsyncMock()), \
             patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.json()["is_first_login"] is True

    def test_returns_400_if_email_already_registered(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = _make_user()
        self.db.execute = AsyncMock(return_value=result)
        resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_missing_email_returns_422(self):
        assert self.client.post(self.url, json={"password": "Secure123"}).status_code == 422

    def test_missing_password_returns_422(self):
        assert self.client.post(self.url, json={"email": USER_EMAIL}).status_code == 422

    def test_short_password_returns_422(self):
        assert self.client.post(self.url, json={"email": USER_EMAIL, "password": "ab1"}).status_code == 422

    def test_password_without_uppercase_returns_422(self):
        assert self.client.post(self.url, json={"email": USER_EMAIL, "password": "nouppercase1"}).status_code == 422

    def test_password_without_digit_returns_422(self):
        assert self.client.post(self.url, json={"email": USER_EMAIL, "password": "NoDigitHere"}).status_code == 422

    @patch("login.app.routes.auth_routes.hash_password", return_value=HASHED_PASSWORD)
    def test_hash_password_called_with_register_password(self, mock_hash):
        self._no_existing_user()
        user = _make_user()
        with patch("login.app.routes.auth_routes.create_user", new=AsyncMock(return_value=user)), \
             patch("login.app.routes.auth_routes.create_auth_credential", new=AsyncMock()), \
             patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH)), \
             patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN), \
             patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            self.client.post(self.url, json=self.PAYLOAD)
        mock_hash.assert_called_once_with("Secure123")

    def test_internal_error_returns_500(self):
        self.db.execute = AsyncMock(side_effect=Exception("DB error"))
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/login
# ══════════════════════════════════════════════════════════════════════════════
class TestLogin:

    PAYLOAD = {"email": USER_EMAIL, "password": RAW_PASSWORD}

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = _make_db_session()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/auth/login"

    def _mock_user_and_cred(self, user=None, cred=None):
        user = user or _make_user()
        cred = cred or _make_auth_cred()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(user),
            _result_returning(cred),
        ])
        return user, cred

    @patch("login.app.routes.auth_routes.verify_password", return_value=True)
    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    def test_returns_200_on_valid_credentials(self, *_):
        self._mock_user_and_cred()
        with patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            assert self.client.post(self.url, json=self.PAYLOAD).status_code == 200

    @patch("login.app.routes.auth_routes.verify_password", return_value=True)
    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    def test_response_contains_access_token(self, *_):
        self._mock_user_and_cred()
        with patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.json()["access_token"] == ACCESS_TOKEN

    @patch("login.app.routes.auth_routes.verify_password", return_value=True)
    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    def test_response_contains_user_email(self, *_):
        self._mock_user_and_cred()
        with patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.json()["user"]["email"] == USER_EMAIL

    def test_returns_401_for_unknown_email(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute = AsyncMock(return_value=result)
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 401

    def test_returns_401_for_wrong_password(self):
        self._mock_user_and_cred()
        with patch("login.app.routes.auth_routes.verify_password", return_value=False):
            assert self.client.post(self.url, json=self.PAYLOAD).status_code == 401

    def test_returns_401_when_no_email_credential(self):
        user = _make_user()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(user),
            _result_returning(None),
        ])
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 401

    def test_returns_401_when_credential_has_no_password_hash(self):
        cred = _make_auth_cred(password_hash=None)
        user = _make_user()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(user),
            _result_returning(cred),
        ])
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 401

    def test_error_message_does_not_reveal_which_field_is_wrong(self):
        """Security: same message for wrong email or wrong password."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute = AsyncMock(return_value=result)
        resp = self.client.post(self.url, json=self.PAYLOAD)
        assert "Invalid email or password" in resp.json()["detail"]

    @patch("login.app.routes.auth_routes.verify_password", return_value=True)
    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    def test_is_first_login_false_when_subscription_tier_set(self, *_):
        user = _make_user(subscription_tier="free")
        self._mock_user_and_cred(user=user)
        with patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.json()["is_first_login"] is False

    @patch("login.app.routes.auth_routes.verify_password", return_value=True)
    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    def test_is_first_login_true_when_no_subscription_tier(self, *_):
        user = _make_user(subscription_tier=None)
        self._mock_user_and_cred(user=user)
        with patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.json()["is_first_login"] is True

    def test_missing_email_returns_422(self):
        assert self.client.post(self.url, json={"password": RAW_PASSWORD}).status_code == 422

    def test_missing_password_returns_422(self):
        assert self.client.post(self.url, json={"email": USER_EMAIL}).status_code == 422

    def test_internal_error_returns_500(self):
        self.db.execute = AsyncMock(side_effect=Exception("DB down"))
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/google
# ══════════════════════════════════════════════════════════════════════════════
class TestGoogleSignIn:

    PAYLOAD = {"token": "google-id-token-abc"}
    GOOGLE_USER_INFO = {
        "google_id": "gid123",
        "email": USER_EMAIL,
        "name": USER_NAME,
        "picture": "https://pic.url",
    }

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = _make_db_session()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/auth/google"

    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    @patch("login.app.routes.auth_routes.verify_google_token", new_callable=AsyncMock)
    def test_returns_200_for_existing_user(self, mock_verify, *_):
        mock_verify.return_value = self.GOOGLE_USER_INFO
        user = _make_user()
        with patch("login.app.routes.auth_routes.get_user_by_email", new=AsyncMock(return_value=user)), \
             patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            assert self.client.post(self.url, json=self.PAYLOAD).status_code == 200

    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    @patch("login.app.routes.auth_routes.verify_google_token", new_callable=AsyncMock)
    def test_creates_new_user_when_not_found(self, mock_verify, *_):
        mock_verify.return_value = self.GOOGLE_USER_INFO
        new_user = _make_user()
        with patch("login.app.routes.auth_routes.get_user_by_email", new=AsyncMock(return_value=None)), \
             patch("login.app.routes.auth_routes.create_user", new=AsyncMock(return_value=new_user)) as mock_create, \
             patch("login.app.routes.auth_routes.create_auth_credential", new=AsyncMock()), \
             patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            self.client.post(self.url, json=self.PAYLOAD)
        mock_create.assert_called_once_with(self.db, USER_EMAIL, USER_NAME)

    @patch("login.app.routes.auth_routes.verify_google_token", new_callable=AsyncMock)
    def test_returns_400_for_invalid_google_token(self, mock_verify):
        mock_verify.side_effect = HTTPException(status_code=400, detail="Invalid Google token")
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 400

    @patch("login.app.routes.auth_routes.verify_google_token", new_callable=AsyncMock)
    def test_returns_500_on_unexpected_error(self, mock_verify):
        mock_verify.side_effect = Exception("Unexpected")
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 500

    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    @patch("login.app.routes.auth_routes.verify_google_token", new_callable=AsyncMock)
    def test_updates_name_if_changed(self, mock_verify, *_):
        mock_verify.return_value = {**self.GOOGLE_USER_INFO, "name": "Updated Name"}
        user = _make_user(name="Old Name")
        with patch("login.app.routes.auth_routes.get_user_by_email", new=AsyncMock(return_value=user)), \
             patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            self.client.post(self.url, json=self.PAYLOAD)
        assert user.name == "Updated Name"

    def test_missing_token_returns_422(self):
        assert self.client.post(self.url, json={}).status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/refresh
# ══════════════════════════════════════════════════════════════════════════════
class TestRefreshToken:

    PAYLOAD = {"refresh_token": REFRESH_TOKEN}

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = _make_db_session()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/auth/refresh"

    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    @patch("login.app.routes.auth_routes.hash_token", return_value=REFRESH_TOKEN_HASH)
    def test_returns_200_with_valid_refresh_token(self, *_):
        rt_record = _make_refresh_token_record()
        user = _make_user()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(rt_record),
            _result_returning(user),
        ])
        with patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            assert self.client.post(self.url, json=self.PAYLOAD).status_code == 200

    @patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH))
    @patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN)
    @patch("login.app.routes.auth_routes.hash_token", return_value=REFRESH_TOKEN_HASH)
    def test_old_token_revoked_after_refresh(self, *_):
        rt_record = _make_refresh_token_record()
        user = _make_user()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(rt_record),
            _result_returning(user),
        ])
        with patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            self.client.post(self.url, json=self.PAYLOAD)
        assert rt_record.revoked is True

    @patch("login.app.routes.auth_routes.hash_token", return_value=REFRESH_TOKEN_HASH)
    def test_returns_401_for_unknown_refresh_token(self, _):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute = AsyncMock(return_value=result)
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 401

    @patch("login.app.routes.auth_routes.hash_token", return_value=REFRESH_TOKEN_HASH)
    def test_returns_401_when_user_not_found(self, _):
        rt_record = _make_refresh_token_record()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(rt_record),
            _result_returning(None),
        ])
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 401

    def test_missing_refresh_token_returns_422(self):
        assert self.client.post(self.url, json={}).status_code == 422

    def test_internal_error_returns_500(self):
        self.db.execute = AsyncMock(side_effect=Exception("DB error"))
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/logout
# ══════════════════════════════════════════════════════════════════════════════
class TestLogout:

    PAYLOAD = {"refresh_token": REFRESH_TOKEN}

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = _make_db_session()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/auth/logout"

    @patch("login.app.routes.auth_routes.hash_token", return_value=REFRESH_TOKEN_HASH)
    def test_returns_200_on_success(self, _):
        rt_record = _make_refresh_token_record()
        result = MagicMock()
        result.scalar_one_or_none.return_value = rt_record
        self.db.execute = AsyncMock(return_value=result)
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 200

    @patch("login.app.routes.auth_routes.hash_token", return_value=REFRESH_TOKEN_HASH)
    def test_response_message_on_logout(self, _):
        rt_record = _make_refresh_token_record()
        result = MagicMock()
        result.scalar_one_or_none.return_value = rt_record
        self.db.execute = AsyncMock(return_value=result)
        assert "Logged out" in self.client.post(self.url, json=self.PAYLOAD).json()["message"]

    @patch("login.app.routes.auth_routes.hash_token", return_value=REFRESH_TOKEN_HASH)
    def test_token_revoked_on_logout(self, _):
        rt_record = _make_refresh_token_record()
        result = MagicMock()
        result.scalar_one_or_none.return_value = rt_record
        self.db.execute = AsyncMock(return_value=result)
        self.client.post(self.url, json=self.PAYLOAD)
        assert rt_record.revoked is True

    @patch("login.app.routes.auth_routes.hash_token", return_value=REFRESH_TOKEN_HASH)
    def test_returns_200_even_if_token_not_found(self, _):
        """Logout is idempotent."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute = AsyncMock(return_value=result)
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 200

    def test_missing_refresh_token_returns_422(self):
        assert self.client.post(self.url, json={}).status_code == 422

    def test_internal_error_returns_500(self):
        self.db.execute = AsyncMock(side_effect=Exception("DB error"))
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# GET /auth/me
# ══════════════════════════════════════════════════════════════════════════════
class TestGetMe:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = _make_db_session()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/auth/me"

    def _override_current_user(self, user):
        from login.app.routes.auth_routes import get_current_user
        self.app.dependency_overrides[get_current_user] = lambda: user

    def test_returns_200_with_valid_token(self):
        self._override_current_user(_make_user())
        assert self.client.get(self.url, headers={"Authorization": "Bearer fake"}).status_code == 200

    def test_returns_user_email(self):
        self._override_current_user(_make_user())
        resp = self.client.get(self.url, headers={"Authorization": "Bearer fake"})
        assert resp.json()["email"] == USER_EMAIL

    def test_returns_user_id(self):
        self._override_current_user(_make_user())
        resp = self.client.get(self.url, headers={"Authorization": "Bearer fake"})
        assert resp.json()["user_id"] == str(USER_ID)

    def test_returns_401_without_token(self):
        assert self.client.get(self.url).status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# PATCH /auth/me
# ══════════════════════════════════════════════════════════════════════════════
class TestUpdateMe:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = _make_db_session()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/auth/me"

    def _override_current_user(self, user):
        from login.app.routes.auth_routes import get_current_user
        self.app.dependency_overrides[get_current_user] = lambda: user

    def test_returns_200_on_name_update(self):
        self._override_current_user(_make_user())
        assert self.client.patch(self.url, json={"name": "New Name"}, headers={"Authorization": "Bearer fake"}).status_code == 200

    def test_name_is_updated_on_user(self):
        user = _make_user()
        self._override_current_user(user)
        self.client.patch(self.url, json={"name": "New Name"}, headers={"Authorization": "Bearer fake"})
        assert user.name == "New Name"

    def test_null_name_does_not_change_existing_name(self):
        user = _make_user(name="Original")
        self._override_current_user(user)
        self.client.patch(self.url, json={}, headers={"Authorization": "Bearer fake"})
        assert user.name == "Original"

    def test_returns_401_without_token(self):
        assert self.client.patch(self.url, json={"name": "X"}).status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# get_current_user dependency (async unit tests)
# ══════════════════════════════════════════════════════════════════════════════
class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_returns_user_for_valid_token(self):
        from login.app.routes.auth_routes import get_current_user
        db = _make_db_session()
        user = _make_user()
        db.execute = AsyncMock(return_value=_result_returning(user))
        with patch("login.app.routes.auth_routes.decode_jwt_token", return_value={"sub": str(USER_ID)}), \
             patch("login.app.routes.auth_routes.enforce_free_plan_expiry", new=AsyncMock(return_value=user)):
            result = await get_current_user(token="valid.token", db=db)
        assert result is user

    @pytest.mark.asyncio
    async def test_raises_401_when_user_not_found(self):
        from login.app.routes.auth_routes import get_current_user
        db = _make_db_session()
        db.execute = AsyncMock(return_value=_result_returning(None))
        with patch("login.app.routes.auth_routes.decode_jwt_token", return_value={"sub": str(USER_ID)}), \
             pytest.raises(HTTPException) as exc:
            await get_current_user(token="token", db=db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_sub_missing_from_payload(self):
        from login.app.routes.auth_routes import get_current_user
        db = _make_db_session()
        with patch("login.app.routes.auth_routes.decode_jwt_token", return_value={}), \
             pytest.raises(HTTPException) as exc:
            await get_current_user(token="token", db=db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_for_invalid_jwt(self):
        from login.app.routes.auth_routes import get_current_user
        db = _make_db_session()
        with patch("login.app.routes.auth_routes.decode_jwt_token",
                   side_effect=HTTPException(status_code=401, detail="Invalid")), \
             pytest.raises(HTTPException) as exc:
            await get_current_user(token="bad.token", db=db)
        assert exc.value.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# enforce_free_plan_expiry
# ══════════════════════════════════════════════════════════════════════════════
class TestEnforceFreePlanExpiry:

    @pytest.mark.asyncio
    async def test_does_nothing_for_non_free_user(self):
        from login.app.routes.auth_routes import enforce_free_plan_expiry
        db = _make_db_session()
        user = _make_user(subscription_tier="pro")
        await enforce_free_plan_expiry(db, user)
        assert user.subscription_tier == "pro"
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_nothing_when_no_expiry_date(self):
        from login.app.routes.auth_routes import enforce_free_plan_expiry
        db = _make_db_session()
        user = _make_user(subscription_tier="free", free_plan_expires_at=None)
        await enforce_free_plan_expiry(db, user)
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_revokes_tier_when_free_plan_expired(self):
        from login.app.routes.auth_routes import enforce_free_plan_expiry
        db = _make_db_session()
        expired = datetime.now(timezone.utc) - timedelta(days=1)
        user = _make_user(subscription_tier="free", free_plan_expires_at=expired)
        await enforce_free_plan_expiry(db, user)
        assert user.subscription_tier is None
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_revoke_when_free_plan_still_active(self):
        from login.app.routes.auth_routes import enforce_free_plan_expiry
        db = _make_db_session()
        future = datetime.now(timezone.utc) + timedelta(days=10)
        user = _make_user(subscription_tier="free", free_plan_expires_at=future)
        await enforce_free_plan_expiry(db, user)
        assert user.subscription_tier == "free"
        db.commit.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# Helper function unit tests
# ══════════════════════════════════════════════════════════════════════════════
class TestHelperFunctions:

    @pytest.mark.asyncio
    async def test_get_user_by_email_returns_user(self):
        from login.app.routes.auth_routes import get_user_by_email
        db = _make_db_session()
        user = _make_user()
        db.execute = AsyncMock(return_value=_result_returning(user))
        assert await get_user_by_email(db, USER_EMAIL) is user

    @pytest.mark.asyncio
    async def test_get_user_by_email_returns_none_when_not_found(self):
        from login.app.routes.auth_routes import get_user_by_email
        db = _make_db_session()
        db.execute = AsyncMock(return_value=_result_returning(None))
        assert await get_user_by_email(db, "nobody@x.com") is None

    @pytest.mark.asyncio
    async def test_create_user_adds_to_session(self):
        from login.app.routes.auth_routes import create_user
        db = _make_db_session()
        with patch("login.app.routes.auth_routes.User") as MockUser:
            mock_user = MagicMock()
            MockUser.return_value = mock_user
            await create_user(db, USER_EMAIL, USER_NAME)
        db.add.assert_called_once_with(mock_user)
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_auth_credential_adds_to_session(self):
        from login.app.routes.auth_routes import create_auth_credential
        db = _make_db_session()
        with patch("login.app.routes.auth_routes.AuthCredential") as MockCred:
            mock_cred = MagicMock()
            MockCred.return_value = mock_cred
            await create_auth_credential(db, USER_ID, "email", HASHED_PASSWORD)
        db.add.assert_called_once_with(mock_cred)

    @pytest.mark.asyncio
    async def test_create_refresh_token_db_adds_to_session(self):
        from login.app.routes.auth_routes import create_refresh_token_db
        db = _make_db_session()
        with patch("login.app.routes.auth_routes.RefreshToken") as MockRT:
            mock_rt = MagicMock()
            MockRT.return_value = mock_rt
            await create_refresh_token_db(db, USER_ID, REFRESH_TOKEN_HASH)
        db.add.assert_called_once_with(mock_rt)

    @pytest.mark.asyncio
    async def test_generate_tokens_returns_required_keys(self):
        from login.app.routes.auth_routes import generate_tokens
        db = _make_db_session()
        user = _make_user()
        with patch("login.app.routes.auth_routes.create_access_token", return_value=ACCESS_TOKEN), \
             patch("login.app.routes.auth_routes.create_refresh_token", return_value=(REFRESH_TOKEN, REFRESH_TOKEN_HASH)), \
             patch("login.app.routes.auth_routes.create_refresh_token_db", new=AsyncMock()):
            tokens = await generate_tokens(db, user)
        for key in ("access_token", "refresh_token", "token_type", "expires_in", "user"):
            assert key in tokens


# ══════════════════════════════════════════════════════════════════════════════
# Router configuration sanity checks
# ══════════════════════════════════════════════════════════════════════════════
class TestRouterConfig:

    def test_router_prefix_is_auth(self):
        from login.app.routes.auth_routes import router
        assert router.prefix == "/auth"

    def test_all_expected_routes_exist(self):
        from login.app.routes.auth_routes import router
        paths = [r.path for r in router.routes]
        for path in ("/register", "/login", "/google", "/refresh", "/logout", "/me"):
            assert path in paths
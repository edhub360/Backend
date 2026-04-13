"""
tests/unit/login/test_password_reset_routes.py
Unit tests for app/password_reset_routes.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

USER_ID    = uuid4()
USER_EMAIL = "reset@example.com"
RAW_TOKEN  = "raw-reset-token-abc"
TOKEN_HASH = "hashed-reset-token"


def _make_user(email=USER_EMAIL):
    u = MagicMock()
    u.user_id = USER_ID
    u.email   = email
    return u

def _make_reset_record(used=False, expired=False):
    r = MagicMock()
    r.user_id = USER_ID
    r.used = used
    r.expires_at = (
        datetime.now(timezone.utc) - timedelta(hours=2) if expired
        else datetime.now(timezone.utc) + timedelta(hours=1)
    )
    return r

def _make_auth_cred():
    c = MagicMock()
    c.password_hash = "$2b$12$oldhash"
    return c

def _result_returning(obj):
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    return result

def _make_app_with_db(mock_db):
    from login.app.routes.password_reset_routes import password_reset_router
    from login.app.db import get_db
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    app = FastAPI()
    app.state.limiter = Limiter(key_func=get_remote_address)
    app.include_router(password_reset_router)
    async def fake_db():
        yield mock_db
    app.dependency_overrides[get_db] = fake_db
    return app


class TestForgotPassword:

    PAYLOAD = {"email": USER_EMAIL}

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/forgot-password"

    @patch("login.app.routes.password_reset_routes.send_reset_password_email")
    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.generate_secure_token", return_value=RAW_TOKEN)
    def test_returns_200_when_user_exists(self, *_):
        with patch("login.app.routes.password_reset_routes.get_user_by_email", new=AsyncMock(return_value=_make_user())):
            assert self.client.post(self.url, json=self.PAYLOAD).status_code == 200

    @patch("login.app.routes.password_reset_routes.send_reset_password_email")
    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.generate_secure_token", return_value=RAW_TOKEN)
    def test_returns_generic_message_when_user_exists(self, *_):
        with patch("login.app.routes.password_reset_routes.get_user_by_email", new=AsyncMock(return_value=_make_user())):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert "reset link has been sent" in resp.json()["message"]

    def test_returns_200_when_user_does_not_exist(self):
        with patch("login.app.routes.password_reset_routes.get_user_by_email", new=AsyncMock(return_value=None)):
            assert self.client.post(self.url, json=self.PAYLOAD).status_code == 200

    def test_same_generic_message_whether_user_exists_or_not(self):
        """Prevents user enumeration via response differences."""
        with patch("login.app.routes.password_reset_routes.get_user_by_email", new=AsyncMock(return_value=None)):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert "reset link has been sent" in resp.json()["message"]

    @patch("login.app.routes.password_reset_routes.send_reset_password_email")
    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.generate_secure_token", return_value=RAW_TOKEN)
    def test_email_sent_when_user_exists(self, mock_gen, mock_hash, mock_send):
        with patch("login.app.routes.password_reset_routes.get_user_by_email", new=AsyncMock(return_value=_make_user())):
            self.client.post(self.url, json=self.PAYLOAD)
        mock_send.assert_called_once()

    def test_email_not_sent_when_user_not_found(self):
        with patch("login.app.routes.password_reset_routes.get_user_by_email", new=AsyncMock(return_value=None)), \
             patch("login.app.routes.password_reset_routes.send_reset_password_email") as mock_send:
            self.client.post(self.url, json=self.PAYLOAD)
        mock_send.assert_not_called()

    @patch("login.app.routes.password_reset_routes.send_reset_password_email")
    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.generate_secure_token", return_value=RAW_TOKEN)
    def test_reset_url_contains_raw_token(self, mock_gen, mock_hash, mock_send):
        with patch("login.app.routes.password_reset_routes.get_user_by_email", new=AsyncMock(return_value=_make_user())):
            self.client.post(self.url, json=self.PAYLOAD)
        reset_url = mock_send.call_args[0][1]
        assert RAW_TOKEN in reset_url

    @patch("login.app.routes.password_reset_routes.send_reset_password_email")
    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.generate_secure_token", return_value=RAW_TOKEN)
    def test_token_hash_stored_not_raw_token(self, *_):
        """Raw token must never be persisted in DB."""
        with patch("login.app.routes.password_reset_routes.get_user_by_email", new=AsyncMock(return_value=_make_user())), \
             patch("login.app.routes.password_reset_routes.PasswordResetToken") as MockPRT:
            MockPRT.return_value = MagicMock()
            self.client.post(self.url, json=self.PAYLOAD)
        assert MockPRT.call_args.kwargs["token_hash"] == TOKEN_HASH

    def test_missing_email_returns_422(self):
        assert self.client.post(self.url, json={}).status_code == 422

    def test_invalid_email_format_returns_422(self):
        assert self.client.post(self.url, json={"email": "not-an-email"}).status_code == 422

    def test_returns_200_on_unexpected_exception(self):
        """Must never leak server error details."""
        with patch("login.app.routes.password_reset_routes.get_user_by_email",
                   new=AsyncMock(side_effect=Exception("DB down"))):
            resp = self.client.post(self.url, json=self.PAYLOAD)
        assert resp.status_code == 200
        assert "reset link has been sent" in resp.json()["message"]


class TestResetPassword:

    PAYLOAD = {"token": RAW_TOKEN, "new_password": "NewSecure1"}

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = AsyncMock()
        self.app = _make_app_with_db(self.db)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.url = "/reset-password"

    def _mock_valid_flow(self):
        reset_record = _make_reset_record()
        user         = _make_user()
        auth_cred    = _make_auth_cred()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(reset_record),
            _result_returning(user),
            _result_returning(auth_cred),
        ])
        return reset_record, user, auth_cred

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.hash_password", return_value="$2b$12$newhash")
    def test_returns_200_on_success(self, *_):
        self._mock_valid_flow()
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 200

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.hash_password", return_value="$2b$12$newhash")
    def test_password_hash_updated_on_credential(self, *_):
        _, _, auth_cred = self._mock_valid_flow()
        self.client.post(self.url, json=self.PAYLOAD)
        assert auth_cred.password_hash == "$2b$12$newhash"

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.hash_password", return_value="$2b$12$newhash")
    def test_reset_token_marked_as_used(self, *_):
        reset_record, _, _ = self._mock_valid_flow()
        self.client.post(self.url, json=self.PAYLOAD)
        assert reset_record.used is True

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    @patch("login.app.routes.password_reset_routes.hash_password", return_value="$2b$12$newhash")
    def test_db_commit_called_on_success(self, *_):
        self._mock_valid_flow()
        self.client.post(self.url, json=self.PAYLOAD)
        self.db.commit.assert_called_once()

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    def test_returns_400_for_invalid_token(self, _):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute = AsyncMock(return_value=result)
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 400

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    def test_returns_400_when_user_not_found(self, _):
        reset_record = _make_reset_record()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(reset_record),
            _result_returning(None),
        ])
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 400

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    def test_returns_400_when_no_email_credential(self, _):
        reset_record = _make_reset_record()
        user = _make_user()
        self.db.execute = AsyncMock(side_effect=[
            _result_returning(reset_record),
            _result_returning(user),
            _result_returning(None),
        ])
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 400

    def test_missing_token_returns_422(self):
        assert self.client.post(self.url, json={"new_password": "NewSecure1"}).status_code == 422

    def test_missing_new_password_returns_422(self):
        assert self.client.post(self.url, json={"token": RAW_TOKEN}).status_code == 422

    def test_weak_password_returns_422(self):
        assert self.client.post(self.url, json={"token": RAW_TOKEN, "new_password": "weak"}).status_code == 422

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    def test_db_rollback_called_on_error(self, _):
        self.db.execute = AsyncMock(side_effect=Exception("DB down"))
        self.client.post(self.url, json=self.PAYLOAD)
        self.db.rollback.assert_called_once()

    @patch("login.app.routes.password_reset_routes.hash_token", return_value=TOKEN_HASH)
    def test_returns_500_on_unexpected_error(self, _):
        self.db.execute = AsyncMock(side_effect=Exception("DB down"))
        assert self.client.post(self.url, json=self.PAYLOAD).status_code == 500
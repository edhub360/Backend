"""
tests/unit/login/test_models.py
================================
Unit tests for login/app/models.py

Coverage:
- User model: fields, defaults, relationships
- AuthCredential model: fields, FK, defaults
- RefreshToken model: fields, FK, revoked default
- PasswordResetToken model: fields, FK, used default
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_user(**kwargs):
    from login.app.models import User
    defaults = dict(
        user_id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
    )
    defaults.update(kwargs)
    u = User(**defaults)
    return u


def _make_auth_cred(**kwargs):
    from login.app.models import AuthCredential
    defaults = dict(
        user_id=uuid.uuid4(),
        provider="email",
        password_hash="$2b$12$fakehash",
    )
    defaults.update(kwargs)
    return AuthCredential(**defaults)


def _make_refresh_token(**kwargs):
    from login.app.models import RefreshToken
    defaults = dict(
        user_id=uuid.uuid4(),
        token_hash="abc123hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    defaults.update(kwargs)
    return RefreshToken(**defaults)


def _make_password_reset_token(**kwargs):
    from login.app.models import PasswordResetToken
    defaults = dict(
        user_id=uuid.uuid4(),
        token_hash="resethash123",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    defaults.update(kwargs)
    return PasswordResetToken(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# User model
# ══════════════════════════════════════════════════════════════════════════════
class TestUserModel:

    def test_tablename_is_users(self):
        from login.app.models import User
        assert User.__tablename__ == "users"

    def test_user_id_is_uuid(self):
        u = _make_user()
        assert isinstance(u.user_id, uuid.UUID)

    def test_user_id_default_is_uuid4(self):
        from login.app.models import User
        u1 = User(email="a@a.com")
        u2 = User(email="b@b.com")
        assert u1.user_id != u2.user_id

    def test_email_field_stored(self):
        u = _make_user(email="hello@example.com")
        assert u.email == "hello@example.com"

    def test_name_field_stored(self):
        u = _make_user(name="Alice")
        assert u.name == "Alice"

    def test_name_is_none_by_default(self):
        from login.app.models import User
        u = User(email="x@x.com")
        assert u.name is None

    def test_language_field_stored(self):
        u = _make_user(language="en")
        assert u.language == "en"

    def test_language_is_none_by_default(self):
        from login.app.models import User
        u = User(email="x@x.com")
        assert u.language is None

    def test_subscription_tier_field_stored(self):
        u = _make_user(subscription_tier="pro")
        assert u.subscription_tier == "pro"

    def test_subscription_tier_is_none_by_default(self):
        from login.app.models import User
        u = User(email="x@x.com")
        assert u.subscription_tier is None

    def test_free_plan_activated_at_stored(self):
        now = datetime.now(timezone.utc)
        u = _make_user(free_plan_activated_at=now)
        assert u.free_plan_activated_at == now

    def test_free_plan_activated_at_is_none_by_default(self):
        from login.app.models import User
        u = User(email="x@x.com")
        assert u.free_plan_activated_at is None

    def test_free_plan_expires_at_stored(self):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        u = _make_user(free_plan_expires_at=future)
        assert u.free_plan_expires_at == future

    def test_free_plan_expires_at_is_none_by_default(self):
        from login.app.models import User
        u = User(email="x@x.com")
        assert u.free_plan_expires_at is None

    def test_has_auth_credentials_relationship(self):
        from login.app.models import User
        assert hasattr(User, "auth_credentials")

    def test_has_refresh_tokens_relationship(self):
        from login.app.models import User
        assert hasattr(User, "refresh_tokens")

    def test_repr_does_not_raise(self):
        u = _make_user()
        str(u)  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# AuthCredential model
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthCredentialModel:

    def test_tablename_is_auth_credentials(self):
        from login.app.models import AuthCredential
        assert AuthCredential.__tablename__ == "auth_credentials"

    def test_user_id_stored(self):
        uid = uuid.uuid4()
        c = _make_auth_cred(user_id=uid)
        assert c.user_id == uid

    def test_provider_defaults_to_email(self):
        from login.app.models import AuthCredential
        c = AuthCredential(user_id=uuid.uuid4())
        assert c.provider == "email"

    def test_provider_can_be_google(self):
        c = _make_auth_cred(provider="google")
        assert c.provider == "google"

    def test_password_hash_stored(self):
        c = _make_auth_cred(password_hash="$2b$12$realhash")
        assert c.password_hash == "$2b$12$realhash"

    def test_password_hash_is_none_for_google(self):
        c = _make_auth_cred(provider="google", password_hash=None)
        assert c.password_hash is None

    def test_has_user_relationship(self):
        from login.app.models import AuthCredential
        assert hasattr(AuthCredential, "user")


# ══════════════════════════════════════════════════════════════════════════════
# RefreshToken model
# ══════════════════════════════════════════════════════════════════════════════
class TestRefreshTokenModel:

    def test_tablename_is_refresh_tokens(self):
        from login.app.models import RefreshToken
        assert RefreshToken.__tablename__ == "refresh_tokens"

    def test_token_id_is_uuid(self):
        rt = _make_refresh_token()
        assert isinstance(rt.token_id, uuid.UUID)

    def test_token_id_unique_per_instance(self):
        rt1 = _make_refresh_token()
        rt2 = _make_refresh_token()
        assert rt1.token_id != rt2.token_id

    def test_user_id_stored(self):
        uid = uuid.uuid4()
        rt = _make_refresh_token(user_id=uid)
        assert rt.user_id == uid

    def test_token_hash_stored(self):
        rt = _make_refresh_token(token_hash="myhash")
        assert rt.token_hash == "myhash"

    def test_expires_at_stored(self):
        future = datetime.now(timezone.utc) + timedelta(days=7)
        rt = _make_refresh_token(expires_at=future)
        assert rt.expires_at == future

    def test_revoked_defaults_to_false(self):
        from login.app.models import RefreshToken
        rt = RefreshToken(
            user_id=uuid.uuid4(),
            token_hash="h",
            expires_at=datetime.now(timezone.utc),
        )
        assert rt.revoked is False

    def test_revoked_can_be_set_to_true(self):
        rt = _make_refresh_token(revoked=True)
        assert rt.revoked is True

    def test_has_user_relationship(self):
        from login.app.models import RefreshToken
        assert hasattr(RefreshToken, "user")


# ══════════════════════════════════════════════════════════════════════════════
# PasswordResetToken model
# ══════════════════════════════════════════════════════════════════════════════
class TestPasswordResetTokenModel:

    def test_tablename_is_password_reset_tokens(self):
        from login.app.models import PasswordResetToken
        assert PasswordResetToken.__tablename__ == "password_reset_tokens"

    def test_token_id_is_uuid(self):
        t = _make_password_reset_token()
        assert isinstance(t.token_id, uuid.UUID)

    def test_token_id_unique_per_instance(self):
        t1 = _make_password_reset_token()
        t2 = _make_password_reset_token()
        assert t1.token_id != t2.token_id

    def test_user_id_stored(self):
        uid = uuid.uuid4()
        t = _make_password_reset_token(user_id=uid)
        assert t.user_id == uid

    def test_token_hash_stored(self):
        t = _make_password_reset_token(token_hash="resethash")
        assert t.token_hash == "resethash"

    def test_expires_at_stored(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        t = _make_password_reset_token(expires_at=future)
        assert t.expires_at == future

    def test_used_defaults_to_false(self):
        from login.app.models import PasswordResetToken
        t = PasswordResetToken(
            user_id=uuid.uuid4(),
            token_hash="h",
            expires_at=datetime.now(timezone.utc),
        )
        assert t.used is False

    def test_used_can_be_set_to_true(self):
        t = _make_password_reset_token(used=True)
        assert t.used is True

    def test_has_user_relationship(self):
        from login.app.models import PasswordResetToken
        assert hasattr(PasswordResetToken, "user")
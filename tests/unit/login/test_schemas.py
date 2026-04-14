"""
tests/unit/login/test_schemas.py
==================================
Unit tests for login/app/schemas.py

Coverage:
- UserBase, UserCreate, UserResponse
- UserUpdate
- GoogleSignInRequest
- EmailRegisterRequest (password validator)
- EmailLoginRequest
- TokenResponse
- RefreshTokenRequest
- ForgotPasswordRequest
- ResetPasswordRequest (password validator)
- LogoutRequest
- ErrorResponse
"""

import pytest
import uuid
from datetime import datetime, timezone
from pydantic import ValidationError


# ══════════════════════════════════════════════════════════════════════════════
# UserBase
# ══════════════════════════════════════════════════════════════════════════════
class TestUserBase:

    def test_valid_email_accepted(self):
        from login.app.schemas import UserBase
        u = UserBase(email="user@example.com")
        assert u.email == "user@example.com"

    def test_invalid_email_raises(self):
        from login.app.schemas import UserBase
        with pytest.raises(ValidationError):
            UserBase(email="not-an-email")

    def test_name_is_optional(self):
        from login.app.schemas import UserBase
        u = UserBase(email="user@example.com")
        assert u.name is None

    def test_name_stored_when_provided(self):
        from login.app.schemas import UserBase
        u = UserBase(email="user@example.com", name="Alice")
        assert u.name == "Alice"


# ══════════════════════════════════════════════════════════════════════════════
# UserCreate
# ══════════════════════════════════════════════════════════════════════════════
class TestUserCreate:

    def test_valid_user_create(self):
        from login.app.schemas import UserCreate
        u = UserCreate(email="user@example.com", name="Bob")
        assert u.email == "user@example.com"

    def test_missing_email_raises(self):
        from login.app.schemas import UserCreate
        with pytest.raises(ValidationError):
            UserCreate()


# ══════════════════════════════════════════════════════════════════════════════
# UserResponse
# ══════════════════════════════════════════════════════════════════════════════
class TestUserResponse:

    def _make(self, **kwargs):
        from login.app.schemas import UserResponse
        defaults = dict(
            user_id=uuid.uuid4(),
            email="user@example.com",
            created_at=datetime.now(timezone.utc),
        )
        defaults.update(kwargs)
        return UserResponse(**defaults)

    def test_valid_response_created(self):
        r = self._make()
        assert r.email == "user@example.com"

    def test_user_id_is_uuid(self):
        uid = uuid.uuid4()
        r = self._make(user_id=uid)
        assert r.user_id == uid

    def test_language_defaults_to_none(self):
        r = self._make()
        assert r.language is None

    def test_subscription_tier_defaults_to_none(self):
        r = self._make()
        assert r.subscription_tier is None

    def test_missing_user_id_raises(self):
        from login.app.schemas import UserResponse
        with pytest.raises(ValidationError):
            UserResponse(email="x@x.com", created_at=datetime.now(timezone.utc))

    def test_missing_created_at_raises(self):
        from login.app.schemas import UserResponse
        with pytest.raises(ValidationError):
            UserResponse(email="x@x.com", user_id=uuid.uuid4())


# ══════════════════════════════════════════════════════════════════════════════
# UserUpdate
# ══════════════════════════════════════════════════════════════════════════════
class TestUserUpdate:

    def test_all_fields_optional(self):
        from login.app.schemas import UserUpdate
        u = UserUpdate()
        assert u.name is None

    def test_name_can_be_set(self):
        from login.app.schemas import UserUpdate
        u = UserUpdate(name="New Name")
        assert u.name == "New Name"

    def test_name_can_be_none(self):
        from login.app.schemas import UserUpdate
        u = UserUpdate(name=None)
        assert u.name is None


# ══════════════════════════════════════════════════════════════════════════════
# GoogleSignInRequest
# ══════════════════════════════════════════════════════════════════════════════
class TestGoogleSignInRequest:

    def test_token_stored(self):
        from login.app.schemas import GoogleSignInRequest
        r = GoogleSignInRequest(token="google-id-token-abc")
        assert r.token == "google-id-token-abc"

    def test_missing_token_raises(self):
        from login.app.schemas import GoogleSignInRequest
        with pytest.raises(ValidationError):
            GoogleSignInRequest()


# ══════════════════════════════════════════════════════════════════════════════
# EmailRegisterRequest — password validator
# ══════════════════════════════════════════════════════════════════════════════
class TestEmailRegisterRequest:

    BASE = {"email": "user@example.com"}

    def test_valid_password_accepted(self):
        from login.app.schemas import EmailRegisterRequest
        r = EmailRegisterRequest(**self.BASE, password="Secure123")
        assert r.password == "Secure123"

    def test_name_is_optional(self):
        from login.app.schemas import EmailRegisterRequest
        r = EmailRegisterRequest(**self.BASE, password="Secure123")
        assert r.name is None

    def test_name_stored_when_provided(self):
        from login.app.schemas import EmailRegisterRequest
        r = EmailRegisterRequest(**self.BASE, password="Secure123", name="Alice")
        assert r.name == "Alice"

    def test_short_password_raises(self):
        from login.app.schemas import EmailRegisterRequest
        with pytest.raises(ValidationError, match="8 characters"):
            EmailRegisterRequest(**self.BASE, password="Ab1")

    def test_password_without_uppercase_raises(self):
        from login.app.schemas import EmailRegisterRequest
        with pytest.raises(ValidationError, match="uppercase"):
            EmailRegisterRequest(**self.BASE, password="nouppercase1")

    def test_password_without_lowercase_raises(self):
        from login.app.schemas import EmailRegisterRequest
        with pytest.raises(ValidationError, match="lowercase"):
            EmailRegisterRequest(**self.BASE, password="NOLOWER123")

    def test_password_without_digit_raises(self):
        from login.app.schemas import EmailRegisterRequest
        with pytest.raises(ValidationError, match="digit"):
            EmailRegisterRequest(**self.BASE, password="NoDigitHere")

    def test_missing_email_raises(self):
        from login.app.schemas import EmailRegisterRequest
        with pytest.raises(ValidationError):
            EmailRegisterRequest(password="Secure123")

    def test_missing_password_raises(self):
        from login.app.schemas import EmailRegisterRequest
        with pytest.raises(ValidationError):
            EmailRegisterRequest(**self.BASE)

    def test_exactly_8_char_valid_password_accepted(self):
        from login.app.schemas import EmailRegisterRequest
        r = EmailRegisterRequest(**self.BASE, password="Secure1!")
        assert r.password == "Secure1!"

    def test_password_7_chars_raises(self):
        from login.app.schemas import EmailRegisterRequest
        with pytest.raises(ValidationError):
            EmailRegisterRequest(**self.BASE, password="Sec1!ab")


# ══════════════════════════════════════════════════════════════════════════════
# EmailLoginRequest
# ══════════════════════════════════════════════════════════════════════════════
class TestEmailLoginRequest:

    def test_valid_login_request(self):
        from login.app.schemas import EmailLoginRequest
        r = EmailLoginRequest(email="user@example.com", password="anypassword")
        assert r.email == "user@example.com"
        assert r.password == "anypassword"

    def test_missing_email_raises(self):
        from login.app.schemas import EmailLoginRequest
        with pytest.raises(ValidationError):
            EmailLoginRequest(password="anypassword")

    def test_missing_password_raises(self):
        from login.app.schemas import EmailLoginRequest
        with pytest.raises(ValidationError):
            EmailLoginRequest(email="user@example.com")

    def test_no_password_strength_validation(self):
        """Login does NOT validate password strength — only registration does."""
        from login.app.schemas import EmailLoginRequest
        r = EmailLoginRequest(email="user@example.com", password="weak")
        assert r.password == "weak"


# ══════════════════════════════════════════════════════════════════════════════
# TokenResponse
# ══════════════════════════════════════════════════════════════════════════════
class TestTokenResponse:

    def _make_user_response(self):
        from login.app.schemas import UserResponse
        return UserResponse(
            user_id=uuid.uuid4(),
            email="user@example.com",
            created_at=datetime.now(timezone.utc),
        )

    def _make(self, **kwargs):
        from login.app.schemas import TokenResponse
        defaults = dict(
            access_token="access.token",
            refresh_token="refresh-token",
            expires_in=3600,
            user=self._make_user_response(),
        )
        defaults.update(kwargs)
        return TokenResponse(**defaults)

    def test_valid_token_response(self):
        t = self._make()
        assert t.access_token == "access.token"

    def test_token_type_defaults_to_bearer(self):
        t = self._make()
        assert t.token_type == "bearer"

    def test_is_first_login_defaults_to_false(self):
        t = self._make()
        assert t.is_first_login is False

    def test_is_first_login_can_be_true(self):
        t = self._make(is_first_login=True)
        assert t.is_first_login is True

    def test_expires_in_stored(self):
        t = self._make(expires_in=7200)
        assert t.expires_in == 7200

    def test_missing_access_token_raises(self):
        from login.app.schemas import TokenResponse
        with pytest.raises(ValidationError):
            TokenResponse(
                refresh_token="r",
                expires_in=3600,
                user=self._make_user_response(),
            )

    def test_missing_user_raises(self):
        from login.app.schemas import TokenResponse
        with pytest.raises(ValidationError):
            TokenResponse(
                access_token="a",
                refresh_token="r",
                expires_in=3600,
            )


# ══════════════════════════════════════════════════════════════════════════════
# RefreshTokenRequest
# ══════════════════════════════════════════════════════════════════════════════
class TestRefreshTokenRequest:

    def test_token_stored(self):
        from login.app.schemas import RefreshTokenRequest
        r = RefreshTokenRequest(refresh_token="my-refresh-token")
        assert r.refresh_token == "my-refresh-token"

    def test_missing_token_raises(self):
        from login.app.schemas import RefreshTokenRequest
        with pytest.raises(ValidationError):
            RefreshTokenRequest()


# ══════════════════════════════════════════════════════════════════════════════
# ForgotPasswordRequest
# ══════════════════════════════════════════════════════════════════════════════
class TestForgotPasswordRequest:

    def test_valid_email_accepted(self):
        from login.app.schemas import ForgotPasswordRequest
        r = ForgotPasswordRequest(email="user@example.com")
        assert r.email == "user@example.com"

    def test_invalid_email_raises(self):
        from login.app.schemas import ForgotPasswordRequest
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="not-an-email")

    def test_missing_email_raises(self):
        from login.app.schemas import ForgotPasswordRequest
        with pytest.raises(ValidationError):
            ForgotPasswordRequest()


# ══════════════════════════════════════════════════════════════════════════════
# ResetPasswordRequest — password validator
# ══════════════════════════════════════════════════════════════════════════════
class TestResetPasswordRequest:

    BASE = {"token": "valid-reset-token"}

    def test_valid_request_accepted(self):
        from login.app.schemas import ResetPasswordRequest
        r = ResetPasswordRequest(**self.BASE, new_password="NewPass1")
        assert r.new_password == "NewPass1"

    def test_token_stored(self):
        from login.app.schemas import ResetPasswordRequest
        r = ResetPasswordRequest(**self.BASE, new_password="NewPass1")
        assert r.token == "valid-reset-token"

    def test_short_password_raises(self):
        from login.app.schemas import ResetPasswordRequest
        with pytest.raises(ValidationError, match="8 characters"):
            ResetPasswordRequest(**self.BASE, new_password="Ab1")

    def test_password_without_uppercase_raises(self):
        from login.app.schemas import ResetPasswordRequest
        with pytest.raises(ValidationError, match="uppercase"):
            ResetPasswordRequest(**self.BASE, new_password="nouppercase1")

    def test_password_without_lowercase_raises(self):
        from login.app.schemas import ResetPasswordRequest
        with pytest.raises(ValidationError, match="lowercase"):
            ResetPasswordRequest(**self.BASE, new_password="NOLOWER123")

    def test_password_without_digit_raises(self):
        from login.app.schemas import ResetPasswordRequest
        with pytest.raises(ValidationError, match="digit"):
            ResetPasswordRequest(**self.BASE, new_password="NoDigitHere")

    def test_missing_token_raises(self):
        from login.app.schemas import ResetPasswordRequest
        with pytest.raises(ValidationError):
            ResetPasswordRequest(new_password="NewPass1")

    def test_missing_new_password_raises(self):
        from login.app.schemas import ResetPasswordRequest
        with pytest.raises(ValidationError):
            ResetPasswordRequest(**self.BASE)


# ══════════════════════════════════════════════════════════════════════════════
# LogoutRequest
# ══════════════════════════════════════════════════════════════════════════════
class TestLogoutRequest:

    def test_token_stored(self):
        from login.app.schemas import LogoutRequest
        r = LogoutRequest(refresh_token="my-refresh-token")
        assert r.refresh_token == "my-refresh-token"

    def test_missing_token_raises(self):
        from login.app.schemas import LogoutRequest
        with pytest.raises(ValidationError):
            LogoutRequest()


# ══════════════════════════════════════════════════════════════════════════════
# ErrorResponse
# ══════════════════════════════════════════════════════════════════════════════
class TestErrorResponse:

    def test_detail_stored(self):
        from login.app.schemas import ErrorResponse
        r = ErrorResponse(detail="Something went wrong")
        assert r.detail == "Something went wrong"

    def test_error_code_is_optional(self):
        from login.app.schemas import ErrorResponse
        r = ErrorResponse(detail="err")
        assert r.error_code is None

    def test_error_code_stored_when_provided(self):
        from login.app.schemas import ErrorResponse
        r = ErrorResponse(detail="err", error_code="AUTH_001")
        assert r.error_code == "AUTH_001"

    def test_missing_detail_raises(self):
        from login.app.schemas import ErrorResponse
        with pytest.raises(ValidationError):
            ErrorResponse()
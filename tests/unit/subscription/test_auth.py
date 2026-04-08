"""
tests/unit/subscription/test_auth.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi import HTTPException
from conftest import make_user


class TestDecodeJwtToken:

    def test_returns_payload_on_valid_token(self):
        from subscription.auth import decode_jwt_token
        uid = str(uuid4())
        with patch("subscription.auth.jwt.decode", return_value={"sub": uid}):
            assert decode_jwt_token("valid.token")["sub"] == uid

    def test_raises_401_on_invalid_token(self):
        from subscription.auth import decode_jwt_token
        from jose import JWTError
        with patch("subscription.auth.jwt.decode", side_effect=JWTError("bad")):
            with pytest.raises(HTTPException) as exc:
                decode_jwt_token("invalid.token")
        assert exc.value.status_code == 401

    def test_error_detail_mentions_validate(self):
        from subscription.auth import decode_jwt_token
        from jose import JWTError
        with patch("subscription.auth.jwt.decode", side_effect=JWTError("bad")):
            with pytest.raises(HTTPException) as exc:
                decode_jwt_token("invalid.token")
        assert "validate" in exc.value.detail.lower()


class TestEnforceFreePlanExpiry:

    @pytest.mark.asyncio
    async def test_resets_tier_when_expired(self, mock_db):
        from subscription.auth import enforce_free_plan_expiry
        expired = datetime.now(timezone.utc) - timedelta(days=1)
        user = make_user(subscription_tier="free", free_plan_expires_at=expired)
        result = await enforce_free_plan_expiry(mock_db, user)
        assert result.subscription_tier is None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(user)

    @pytest.mark.asyncio
    async def test_no_reset_when_still_active(self, mock_db):
        from subscription.auth import enforce_free_plan_expiry
        future = datetime.now(timezone.utc) + timedelta(days=30)
        user = make_user(subscription_tier="free", free_plan_expires_at=future)
        result = await enforce_free_plan_expiry(mock_db, user)
        assert result.subscription_tier == "free"
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_reset_when_tier_not_free(self, mock_db):
        from subscription.auth import enforce_free_plan_expiry
        expired = datetime.now(timezone.utc) - timedelta(days=1)
        user = make_user(subscription_tier="pro", free_plan_expires_at=expired)
        result = await enforce_free_plan_expiry(mock_db, user)
        assert result.subscription_tier == "pro"
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_reset_when_no_expiry_set(self, mock_db):
        from subscription.auth import enforce_free_plan_expiry
        user = make_user(subscription_tier="free", free_plan_expires_at=None)
        result = await enforce_free_plan_expiry(mock_db, user)
        assert result.subscription_tier == "free"
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_always_returns_user(self, mock_db):
        from subscription.auth import enforce_free_plan_expiry
        user = make_user()
        result = await enforce_free_plan_expiry(mock_db, user)
        assert result is user


class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_returns_user_for_valid_token(self, mock_db):
        from subscription.auth import get_current_user
        user = make_user()
        uid = str(user.user_id)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = result_mock
        with patch("subscription.auth.decode_jwt_token", return_value={"sub": uid}), \
             patch("subscription.auth.enforce_free_plan_expiry", new=AsyncMock(return_value=user)):
            result = await get_current_user(token="valid.token", db=mock_db)
        assert result is user

    @pytest.mark.asyncio
    async def test_raises_401_when_sub_missing(self, mock_db):
        from subscription.auth import get_current_user
        with patch("subscription.auth.decode_jwt_token", return_value={}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(token="valid.token", db=mock_db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_user_not_in_db(self, mock_db):
        from subscription.auth import get_current_user
        uid = str(uuid4())
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock
        with patch("subscription.auth.decode_jwt_token", return_value={"sub": uid}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(token="valid.token", db=mock_db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_enforce_expiry_called_on_every_request(self, mock_db):
        from subscription.auth import get_current_user
        user = make_user()
        uid = str(user.user_id)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = result_mock
        with patch("subscription.auth.decode_jwt_token", return_value={"sub": uid}), \
             patch("subscription.auth.enforce_free_plan_expiry",
                   new=AsyncMock(return_value=user)) as mock_enforce:
            await get_current_user(token="valid.token", db=mock_db)
        mock_enforce.assert_called_once_with(mock_db, user)

    # test_auth.py — add these two tests to TestGetCurrentUser

    @pytest.mark.asyncio
    async def test_raises_401_on_malformed_uuid(self, mock_db):
        from subscription.auth import get_current_user
        with patch("subscription.auth.decode_jwt_token", return_value={"sub": "not-a-uuid"}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(token="valid.token", db=mock_db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_on_unexpected_db_error(self, mock_db):
        from subscription.auth import get_current_user
        uid = str(uuid4())
        mock_db.execute.side_effect = Exception("DB connection lost")
        with patch("subscription.auth.decode_jwt_token", return_value={"sub": uid}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(token="valid.token", db=mock_db)
        assert exc.value.status_code == 401
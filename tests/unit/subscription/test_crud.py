"""
tests/unit/subscription/test_crud.py
All async DB operations tested with pure mocks — no DB connection.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from conftest import make_plan, make_price, make_customer, make_subscription, make_user


def _exec_returns(mock_db, value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = value if isinstance(value, list) else []
    result.scalars.return_value.first.return_value = value
    mock_db.execute.return_value = result
    return result


class TestGetCustomer:

    @pytest.mark.asyncio
    async def test_returns_customer_when_found(self, mock_db):
        from subscription.crud import get_customer
        customer = make_customer()
        _exec_returns(mock_db, customer)
        assert await get_customer(mock_db, customer.user_id) is customer

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        from subscription.crud import get_customer
        _exec_returns(mock_db, None)
        assert await get_customer(mock_db, uuid4()) is None


class TestGetPlan:

    @pytest.mark.asyncio
    async def test_returns_plan_when_found(self, mock_db):
        from subscription.crud import get_plan
        plan = make_plan()
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = plan
        mock_db.execute.return_value = result_mock
        assert await get_plan(mock_db, plan.id) is plan

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        from subscription.crud import get_plan
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock
        assert await get_plan(mock_db, uuid4()) is None


class TestGetAllPlans:

    @pytest.mark.asyncio
    async def test_returns_list_of_plans(self, mock_db):
        from subscription.crud import get_all_plans
        plans = [make_plan("Pro"), make_plan("Basic")]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = plans
        mock_db.execute.return_value = result_mock
        assert await get_all_plans(mock_db) == plans

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, mock_db):
        from subscription.crud import get_all_plans
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_mock
        assert await get_all_plans(mock_db) == []


class TestCreateCustomer:

    @pytest.mark.asyncio
    async def test_returns_customer_after_creation(self, mock_db):
        from subscription.crud import create_customer
        customer = make_customer()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = customer
        mock_db.execute.return_value = result_mock
        result = await create_customer(mock_db, customer.user_id, "cus_stripe_id")
        assert result is customer

    @pytest.mark.asyncio
    async def test_calls_db_commit(self, mock_db):
        from subscription.crud import create_customer
        customer = make_customer()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = customer
        mock_db.execute.return_value = result_mock
        await create_customer(mock_db, customer.user_id, "cus_stripe_id")
        mock_db.commit.assert_called_once()


class TestGetPlanPrice:

    @pytest.mark.asyncio
    async def test_returns_price_when_found(self, mock_db):
        from subscription.crud import get_plan_price
        price = make_price()
        _exec_returns(mock_db, price)
        assert await get_plan_price(mock_db, price.plan_id, "monthly") is price

    @pytest.mark.asyncio
    async def test_returns_none_for_inactive(self, mock_db):
        from subscription.crud import get_plan_price
        _exec_returns(mock_db, None)
        assert await get_plan_price(mock_db, uuid4(), "yearly") is None


class TestGetUserSubscription:

    @pytest.mark.asyncio
    async def test_returns_active_subscription(self, mock_db):
        from subscription.crud import get_user_subscription
        sub = make_subscription()
        _exec_returns(mock_db, sub)
        assert await get_user_subscription(mock_db, uuid4()) is sub

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        from subscription.crud import get_user_subscription
        _exec_returns(mock_db, None)
        assert await get_user_subscription(mock_db, uuid4()) is None


class TestCreateSubscription:

    @pytest.mark.asyncio
    async def test_returns_subscription_with_correct_stripe_id(self, mock_db):
        from subscription.crud import create_subscription
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh
        now = datetime.now(timezone.utc)
        result = await create_subscription(
            mock_db, uuid4(), uuid4(), "sub_stripe_id", now, now + timedelta(days=30)
        )
        assert result.stripe_subscription_id == "sub_stripe_id"

    @pytest.mark.asyncio
    async def test_status_defaults_to_active(self, mock_db):
        from subscription.crud import create_subscription
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh
        now = datetime.now(timezone.utc)
        result = await create_subscription(
            mock_db, uuid4(), uuid4(), "sub_stripe_id", now, now + timedelta(days=30)
        )
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_db_add_and_commit_called(self, mock_db):
        from subscription.crud import create_subscription
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh
        now = datetime.now(timezone.utc)
        await create_subscription(
            mock_db, uuid4(), uuid4(), "sub_stripe_id", now, now + timedelta(days=30)
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestUpdateSubscription:

    @pytest.mark.asyncio
    async def test_updates_status_field(self, mock_db):
        from subscription.crud import update_subscription
        sub = make_subscription(status="active")
        _exec_returns(mock_db, sub)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh
        result = await update_subscription(mock_db, sub.id, status="cancelled")
        assert result.status == "cancelled"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        from subscription.crud import update_subscription
        _exec_returns(mock_db, None)
        assert await update_subscription(mock_db, uuid4(), status="cancelled") is None

    @pytest.mark.asyncio
    async def test_commits_when_found(self, mock_db):
        from subscription.crud import update_subscription
        sub = make_subscription()
        _exec_returns(mock_db, sub)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh
        await update_subscription(mock_db, sub.id, status="cancelled")
        mock_db.commit.assert_called_once()


class TestGetSubscriptionByStripeId:

    @pytest.mark.asyncio
    async def test_returns_subscription_when_found(self, mock_db):
        from subscription.crud import get_subscription_by_stripe_id
        sub = make_subscription()
        _exec_returns(mock_db, sub)
        assert await get_subscription_by_stripe_id(mock_db, "sub_test_fake") is sub

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        from subscription.crud import get_subscription_by_stripe_id
        _exec_returns(mock_db, None)
        assert await get_subscription_by_stripe_id(mock_db, "sub_unknown") is None


class TestDeletePlanFromStripe:

    @pytest.mark.asyncio
    async def test_soft_deletes_plan(self, mock_db):
        from subscription.crud import delete_plan_from_stripe
        plan = make_plan(active=True)
        _exec_returns(mock_db, plan)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh
        await delete_plan_from_stripe(mock_db, "prod_abc")
        assert plan.is_active is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        from subscription.crud import delete_plan_from_stripe
        _exec_returns(mock_db, None)
        assert await delete_plan_from_stripe(mock_db, "prod_unknown") is None


class TestDeletePlanPriceFromStripe:

    @pytest.mark.asyncio
    async def test_soft_deletes_price(self, mock_db):
        from subscription.crud import delete_plan_price_from_stripe
        price = make_price(active=True)
        _exec_returns(mock_db, price)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh
        await delete_plan_price_from_stripe(mock_db, "price_test_monthly")
        assert price.is_active is False

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        from subscription.crud import delete_plan_price_from_stripe
        _exec_returns(mock_db, None)
        assert await delete_plan_price_from_stripe(mock_db, "price_unknown") is None


class TestFreePlanHelpers:

    @pytest.mark.asyncio
    async def test_has_used_true_when_activated(self, mock_db):
        from subscription.crud import has_used_free_plan
        user = make_user(free_plan_activated_at=datetime.now(timezone.utc))
        assert await has_used_free_plan(mock_db, user) is True

    @pytest.mark.asyncio
    async def test_has_used_false_when_never_activated(self, mock_db):
        from subscription.crud import has_used_free_plan
        user = make_user(free_plan_activated_at=None)
        assert await has_used_free_plan(mock_db, user) is False

    @pytest.mark.asyncio
    async def test_expired_true_when_past_expiry(self):
        from subscription.crud import is_free_plan_expired
        past = datetime.now(timezone.utc) - timedelta(days=1)
        assert await is_free_plan_expired(make_user(free_plan_expires_at=past)) is True

    @pytest.mark.asyncio
    async def test_expired_false_when_future(self):
        from subscription.crud import is_free_plan_expired
        future = datetime.now(timezone.utc) + timedelta(days=1)
        assert await is_free_plan_expired(make_user(free_plan_expires_at=future)) is False

    @pytest.mark.asyncio
    async def test_expired_false_when_no_expiry(self):
        from subscription.crud import is_free_plan_expired
        assert await is_free_plan_expired(make_user(free_plan_expires_at=None)) is False
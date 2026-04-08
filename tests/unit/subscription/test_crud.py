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

# ── add after TestGetSubscriptionByStripeId ─────────────────────────────────

class TestGetPlanPriceByStripeId:

    @pytest.mark.asyncio
    async def test_returns_price_when_found(self, mock_db):
        from subscription.crud import get_plan_price_by_stripe_id
        price = make_price()
        _exec_returns(mock_db, price)
        assert await get_plan_price_by_stripe_id(mock_db, "price_abc") is price

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        from subscription.crud import get_plan_price_by_stripe_id
        _exec_returns(mock_db, None)
        assert await get_plan_price_by_stripe_id(mock_db, "price_unknown") is None


class TestCreatePlanFromStripe:

    def _stripe_product(self, product_id="prod_123", active=True):
        return {
            "id": product_id,
            "name": "Pro Plan",
            "description": "All pro features",
            "active": active,
            "metadata": {"tier": "pro", "max_students": "500"},
        }

    @pytest.mark.asyncio
    async def test_creates_new_plan_when_not_existing(self, mock_db):
        from subscription.crud import create_plan_from_stripe

        # First execute → no existing plan; second execute → refresh
        _exec_returns(mock_db, None)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        result = await create_plan_from_stripe(mock_db, self._stripe_product())

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.stripe_product_id == "prod_123"
        assert added.name == "Pro Plan"
        assert added.features_json == {"tier": "pro", "max_students": "500"}
        assert added.is_active is True

    @pytest.mark.asyncio
    async def test_returns_existing_plan_without_creating(self, mock_db):
        from subscription.crud import create_plan_from_stripe
        existing = make_plan()
        _exec_returns(mock_db, existing)

        result = await create_plan_from_stripe(mock_db, self._stripe_product())

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        assert result is existing

    @pytest.mark.asyncio
    async def test_inactive_product_creates_inactive_plan(self, mock_db):
        from subscription.crud import create_plan_from_stripe
        _exec_returns(mock_db, None)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        await create_plan_from_stripe(mock_db, self._stripe_product(active=False))

        added = mock_db.add.call_args[0][0]
        assert added.is_active is False


class TestUpdatePlanFromStripe:

    def _stripe_product(self, product_id="prod_123", name="Updated Plan", active=True):
        return {
            "id": product_id,
            "name": name,
            "description": "Updated desc",
            "active": active,
            "metadata": {"tier": "updated"},
        }

    @pytest.mark.asyncio
    async def test_updates_existing_plan_fields(self, mock_db):
        from subscription.crud import update_plan_from_stripe
        plan = make_plan(name="Old Name", active=True)
        _exec_returns(mock_db, plan)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        result = await update_plan_from_stripe(mock_db, self._stripe_product(name="Updated Plan"))

        assert result.name == "Updated Plan"
        assert result.description == "Updated desc"
        assert result.features_json == {"tier": "updated"}
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_plan_when_not_found(self, mock_db):
        from subscription.crud import update_plan_from_stripe
        # Both execute calls return None (check-existing + create's check)
        _exec_returns(mock_db, None)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        await update_plan_from_stripe(mock_db, self._stripe_product())

        # add() called inside create_plan_from_stripe
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivates_plan_when_stripe_inactive(self, mock_db):
        from subscription.crud import update_plan_from_stripe
        plan = make_plan(active=True)
        _exec_returns(mock_db, plan)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        await update_plan_from_stripe(mock_db, self._stripe_product(active=False))

        assert plan.is_active is False


class TestCreatePlanPriceFromStripe:

    def _stripe_price(self, price_id="price_123", product_id="prod_123", active=True):
        return {
            "id": price_id,
            "product": product_id,
            "currency": "inr",
            "unit_amount": 49900,   # 499 rupees in paise
            "active": active,
            "recurring": {"interval": "month"},
        }

    def _setup_db_sequence(self, mock_db, existing_price, plan):
        """Execute is called twice: check existing price, then find plan."""
        calls = [existing_price, plan]
        idx = 0
        def side_effect(query, *args, **kwargs):
            nonlocal idx
            result = MagicMock()
            result.scalar_one_or_none.return_value = calls[idx]
            idx = min(idx + 1, len(calls) - 1)
            return result
        mock_db.execute.side_effect = side_effect

    @pytest.mark.asyncio
    async def test_creates_new_price_with_correct_fields(self, mock_db):
        from subscription.crud import create_plan_price_from_stripe
        plan = make_plan()
        self._setup_db_sequence(mock_db, existing_price=None, plan=plan)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        result = await create_plan_price_from_stripe(mock_db, self._stripe_price())

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.stripe_price_id == "price_123"
        assert added.billing_period == "month"
        assert added.amount == 499          # paise → rupees
        assert added.currency == "INR"
        assert added.plan_id == plan.id

    @pytest.mark.asyncio
    async def test_returns_existing_price_without_creating(self, mock_db):
        from subscription.crud import create_plan_price_from_stripe
        existing = make_price()
        _exec_returns(mock_db, existing)

        result = await create_plan_price_from_stripe(mock_db, self._stripe_price())

        mock_db.add.assert_not_called()
        assert result is existing

    @pytest.mark.asyncio
    async def test_returns_none_when_plan_not_found(self, mock_db):
        from subscription.crud import create_plan_price_from_stripe
        # price doesn't exist, plan also not found
        self._setup_db_sequence(mock_db, existing_price=None, plan=None)

        result = await create_plan_price_from_stripe(mock_db, self._stripe_price())

        mock_db.add.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_one_time_price_sets_billing_period(self, mock_db):
        from subscription.crud import create_plan_price_from_stripe
        plan = make_plan()
        self._setup_db_sequence(mock_db, existing_price=None, plan=plan)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        stripe_price = self._stripe_price()
        stripe_price["recurring"] = None   # one-time price

        await create_plan_price_from_stripe(mock_db, stripe_price)

        added = mock_db.add.call_args[0][0]
        assert added.billing_period == "one_time"


class TestUpdatePlanPriceFromStripe:

    def _stripe_price(self, price_id="price_123", active=True):
        return {
            "id": price_id,
            "product": "prod_123",
            "currency": "inr",
            "unit_amount": 49900,
            "active": active,
            "recurring": {"interval": "month"},
        }

    @pytest.mark.asyncio
    async def test_deactivates_existing_price(self, mock_db):
        from subscription.crud import update_plan_price_from_stripe
        price = make_price(active=True)
        _exec_returns(mock_db, price)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        result = await update_plan_price_from_stripe(mock_db, self._stripe_price(active=False))

        assert price.is_active is False
        mock_db.commit.assert_called_once()
        assert result is price

    @pytest.mark.asyncio
    async def test_reactivates_existing_price(self, mock_db):
        from subscription.crud import update_plan_price_from_stripe
        price = make_price(active=False)
        _exec_returns(mock_db, price)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        result = await update_plan_price_from_stripe(mock_db, self._stripe_price(active=True))

        assert price.is_active is True

    @pytest.mark.asyncio
    async def test_creates_price_when_not_found(self, mock_db):
        from subscription.crud import update_plan_price_from_stripe
        # First call → no existing price; delegates to create_plan_price_from_stripe
        # which then calls execute twice more (check existing + find plan), both None
        _exec_returns(mock_db, None)
        async def fake_refresh(obj): pass
        mock_db.refresh = fake_refresh

        result = await update_plan_price_from_stripe(mock_db, self._stripe_price())

        # Result is None because plan also not found inside create_plan_price_from_stripe
        assert result is None
        mock_db.add.assert_not_called()

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
"""
tests/unit/subscription/test_main.py
FastAPI route tests using httpx.AsyncClient + ASGITransport.
All DB and Stripe calls are patched — no real network or DB connections.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from conftest import (
    make_customer, make_subscription, make_price,
    make_plan, make_user
)

# ── App import (modules already aliased in conftest.py) ───────────────────
from subscription.main import app
from subscription.db import get_db


# ── Shared DB override ────────────────────────────────────────────────────

def _override_db(mock_db):
    """Return a FastAPI dependency override that yields mock_db."""
    async def _dep():
        yield mock_db
    return _dep


# ─────────────────────────────────────────────────────────────────────────
# POST /checkout
# ─────────────────────────────────────────────────────────────────────────

class TestCreateCheckoutSession:

    @pytest.mark.asyncio
    async def test_returns_checkout_url_existing_customer(self, mock_db):
        customer = make_customer()
        price    = make_price(stripe_price_id="price_abc")
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_customer",      new=AsyncMock(return_value=customer)), \
             patch("subscription.main.get_plan_price",    new=AsyncMock(return_value=price)), \
             patch("subscription.main.StripeClient.create_checkout_session",
                   return_value="https://checkout.stripe.com/pay/cs_test"):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/checkout", json={
                    "user_id": str(uuid4()),
                    "plan_id": str(uuid4()),
                    "billing_period": "monthly"
                })

        assert resp.status_code == 200
        assert "url" in resp.json()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_creates_new_stripe_customer_when_not_found(self, mock_db):
        new_customer = make_customer()
        price        = make_price(stripe_price_id="price_abc")
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_customer",      new=AsyncMock(return_value=None)), \
             patch("subscription.main.StripeClient.create_customer",
                   return_value="cus_new_stripe"), \
             patch("subscription.main.create_customer",   new=AsyncMock(return_value=new_customer)), \
             patch("subscription.main.get_plan_price",    new=AsyncMock(return_value=price)), \
             patch("subscription.main.StripeClient.create_checkout_session",
                   return_value="https://checkout.stripe.com/pay/cs_test"):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/checkout", json={
                    "user_id": str(uuid4()),
                    "plan_id": str(uuid4()),
                    "billing_period": "monthly"
                })

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_404_when_price_not_found(self, mock_db):
        customer = make_customer()
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_customer",   new=AsyncMock(return_value=customer)), \
             patch("subscription.main.get_plan_price", new=AsyncMock(return_value=None)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/checkout", json={
                    "user_id": str(uuid4()),
                    "plan_id": str(uuid4()),
                    "billing_period": "monthly"
                })

        assert resp.status_code == 404
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_metadata_contains_user_id(self, mock_db):
        customer = make_customer()
        price    = make_price(stripe_price_id="price_abc")
        user_id  = str(uuid4())
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_customer",   new=AsyncMock(return_value=customer)), \
             patch("subscription.main.get_plan_price", new=AsyncMock(return_value=price)), \
             patch("subscription.main.StripeClient.create_checkout_session",
                   return_value="https://checkout.stripe.com/pay/cs_test") as mock_checkout:

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.post("/checkout", json={
                    "user_id": user_id,
                    "plan_id": str(uuid4()),
                    "billing_period": "monthly"
                })

        call_kwargs = mock_checkout.call_args
        metadata = call_kwargs[0][4] if call_kwargs[0] else call_kwargs[1].get("metadata", {})
        assert metadata.get("user_id") == user_id
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────
# GET /plans
# ─────────────────────────────────────────────────────────────────────────

class TestGetPlans:

    def setup_method(self):
        # Reset cache state before each test
        import subscription.main as main_module
        main_module.PLANS_CACHE = None
        main_module.CACHE_EXPIRY = None

    @pytest.mark.asyncio
    async def test_returns_list_of_plans(self, mock_db):
        import subscription.main as main_mod
        main_mod.PLANS_CACHE = None
        main_mod.CACHE_EXPIRY = None
        app.dependency_overrides[get_db] = _override_db(mock_db)

        plan  = make_plan("Pro")
        price = make_price(plan_id=plan.id)
        plan.prices = [price]

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [plan]
        mock_db.execute.return_value = result_mock

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/plans")

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_cached_plans_on_second_call(self, mock_db):
        import subscription.main as main_mod
        cached = [{"id": str(uuid4()), "name": "Pro", "description": "x",
                   "features_json": {}, "is_active": True, "prices": []}]
        main_mod.PLANS_CACHE  = cached
        main_mod.CACHE_EXPIRY = datetime.now() + timedelta(minutes=30)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/plans")

        assert resp.status_code == 200
        mock_db.execute.assert_not_called()
        app.dependency_overrides.clear()
        main_mod.PLANS_CACHE  = None
        main_mod.CACHE_EXPIRY = None
    
    @pytest.mark.asyncio
    async def test_returns_cached_plans_when_cache_valid(self, mock_db):
        import subscription.main as main_module
        from subscription.main import get_cached_plans
        from datetime import datetime, timedelta

        main_module.PLANS_CACHE = [{"id": "cached-plan"}]
        main_module.CACHE_EXPIRY = datetime.now() + timedelta(minutes=10)

        result = await get_cached_plans(mock_db)

        mock_db.execute.assert_not_called()   # DB never touched
        assert result == [{"id": "cached-plan"}]

# ─────────────────────────────────────────────────────────────────────────
# GET /subscriptions/{user_id}
# ─────────────────────────────────────────────────────────────────────────

class TestGetSubscriptionByUserId:

    @pytest.mark.asyncio
    async def test_returns_paid_subscription_when_found(self, mock_db):
        sub = make_subscription()
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_user_subscription", new=AsyncMock(return_value=sub)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/subscriptions/{uuid4()}")

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_free_plan_when_no_paid_sub(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)
        now    = datetime.now(timezone.utc)
        future = now + timedelta(days=3)

        row_mock = MagicMock()
        row_mock.subscription_tier     = "free"
        row_mock.free_plan_activated_at = now
        row_mock.free_plan_expires_at   = future

        exec_result = MagicMock()
        exec_result.fetchone.return_value = row_mock

        with patch("subscription.main.get_user_subscription", new=AsyncMock(return_value=None)), \
             patch.object(mock_db, "execute", new=AsyncMock(return_value=exec_result)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/subscriptions/{uuid4()}")

        assert resp.status_code == 200
        assert resp.json()["plan"] == "free"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_404_when_no_subscription_at_all(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)

        exec_result = MagicMock()
        exec_result.fetchone.return_value = None

        with patch("subscription.main.get_user_subscription", new=AsyncMock(return_value=None)), \
             patch.object(mock_db, "execute", new=AsyncMock(return_value=exec_result)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/subscriptions/{uuid4()}")

        assert resp.status_code == 404
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_free_plan_expired_returns_expired_status(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)
        now  = datetime.now(timezone.utc)
        past = now - timedelta(days=1)

        row_mock = MagicMock()
        row_mock.subscription_tier      = "free"
        row_mock.free_plan_activated_at = now - timedelta(days=8)
        row_mock.free_plan_expires_at   = past

        exec_result = MagicMock()
        exec_result.fetchone.return_value = row_mock

        with patch("subscription.main.get_user_subscription", new=AsyncMock(return_value=None)), \
             patch.object(mock_db, "execute", new=AsyncMock(return_value=exec_result)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/subscriptions/{uuid4()}")

        assert resp.json()["status"] == "expired"
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────
# POST /subscriptions/{user_id}/cancel
# ─────────────────────────────────────────────────────────────────────────

class TestCancelSubscription:

    @pytest.mark.asyncio
    async def test_returns_200_with_message(self, mock_db):
        sub = make_subscription(stripe_sub_id="sub_abc")
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_user_subscription", new=AsyncMock(return_value=sub)), \
             patch("subscription.main.StripeClient.cancel_subscription"):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/subscriptions/{uuid4()}/cancel",
                    json={"cancel_at_period_end": True}
                )

        assert resp.status_code == 200
        assert "message" in resp.json()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_404_when_no_subscription(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_user_subscription", new=AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/subscriptions/{uuid4()}/cancel",
                    json={"cancel_at_period_end": True}
                )

        assert resp.status_code == 404
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_passes_cancel_at_period_end_false(self, mock_db):
        sub = make_subscription(stripe_sub_id="sub_abc")
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_user_subscription", new=AsyncMock(return_value=sub)), \
             patch("subscription.main.StripeClient.cancel_subscription") as mock_cancel:

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.post(
                    f"/subscriptions/{uuid4()}/cancel",
                    json={"cancel_at_period_end": False}
                )

        mock_cancel.assert_called_once_with("sub_abc", False)
        app.dependency_overrides.clear()

# ─────────────────────────────────────────────────────────────────────────
# GET /payment-methods/{user_id}
# ─────────────────────────────────────────────────────────────────────────

class TestGetPaymentMethods:

    @pytest.mark.asyncio
    async def test_returns_payment_methods_for_known_customer(self, mock_db):
        customer = make_customer()
        app.dependency_overrides[get_db] = _override_db(mock_db)
        pm = {"id": "pm_abc", "brand": "visa", "last4": "4242",
              "exp_month": 12, "exp_year": 2027, "is_default": True}

        with patch("subscription.main.get_customer", new=AsyncMock(return_value=customer)), \
             patch("subscription.main.StripeClient.get_payment_methods", return_value=[pm]):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/payment-methods/{uuid4()}")

        assert resp.status_code == 200
        assert resp.json()["has_payment_method"] is True
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_empty_when_customer_not_found(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_customer", new=AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/payment-methods/{uuid4()}")

        assert resp.status_code == 200
        assert resp.json()["has_payment_method"] is False
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_customer_v2(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)
        with patch("subscription.main.get_customer", new=AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get(f"/payment-methods/{uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["payment_methods"] == []
        assert resp.json()["has_payment_method"] is False
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_payment_methods_when_found_v2(self, mock_db):
        customer = make_customer()
        app.dependency_overrides[get_db] = _override_db(mock_db)
        with patch("subscription.main.get_customer", new=AsyncMock(return_value=customer)), \
             patch("subscription.main.StripeClient.get_payment_methods",
                   return_value=[{"id": "pm_abc", "type": "card"}]):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get(f"/payment-methods/{uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["has_payment_method"] is True
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_500_on_stripe_error_v2(self, mock_db):
        customer = make_customer()
        app.dependency_overrides[get_db] = _override_db(mock_db)
        with patch("subscription.main.get_customer", new=AsyncMock(return_value=customer)), \
             patch("subscription.main.StripeClient.get_payment_methods",
                   side_effect=Exception("Stripe down")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get(f"/payment-methods/{uuid4()}")
        assert resp.status_code == 500
        app.dependency_overrides.clear()

# ─────────────────────────────────────────────────────────────────────────
# POST /create-customer-portal-session
# ─────────────────────────────────────────────────────────────────────────

class TestCreateCustomerPortalSession:

    @pytest.mark.asyncio
    async def test_returns_portal_url(self, mock_db):
        customer = make_customer()
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_customer", new=AsyncMock(return_value=customer)), \
             patch("subscription.main.StripeClient.create_customer_portal_session",
                   return_value="https://billing.stripe.com/session/abc"):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/create-customer-portal-session",
                                         json={"user_id": str(uuid4())})

        assert resp.status_code == 200
        assert "billing.stripe.com" in resp.json()["url"]
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_404_when_customer_not_found(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.get_customer", new=AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/create-customer-portal-session",
                                         json={"user_id": str(uuid4())})

        assert resp.status_code == 404
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_400_on_invalid_user_id(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/create-customer-portal-session",
                                     json={"user_id": "not-a-uuid"})

        assert resp.status_code == 400
        app.dependency_overrides.clear()


    @pytest.mark.asyncio
    async def test_returns_500_on_stripe_error_v2(self, mock_db):
        customer = make_customer()
        app.dependency_overrides[get_db] = _override_db(mock_db)
        with patch("subscription.main.get_customer", new=AsyncMock(return_value=customer)), \
             patch("subscription.main.StripeClient.create_customer_portal_session",
                   side_effect=Exception("Portal unavailable")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/create-customer-portal-session",
                                     json={"user_id": str(uuid4())})
        assert resp.status_code == 500
        app.dependency_overrides.clear()
# ─────────────────────────────────────────────────────────────────────────
# POST /activate-subscription
# ─────────────────────────────────────────────────────────────────────────

class TestActivateSubscription:

    def _auth_override(self, user):
        from subscription.auth import get_current_user
        async def _dep():
            return user
        app.dependency_overrides[get_current_user] = _dep

    @pytest.mark.asyncio
    async def test_activates_free_plan_first_time(self, mock_db):
        user = make_user(subscription_tier=None, free_plan_activated_at=None)
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/activate-subscription")

        assert resp.status_code == 200
        assert resp.json()["status"] == "activated"
        assert resp.json()["subscription_tier"] == "free"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_already_active_when_still_valid(self, mock_db):
        future = datetime.now(timezone.utc) + timedelta(days=5)
        user = make_user(
            subscription_tier="free",
            free_plan_activated_at=datetime.now(timezone.utc) - timedelta(days=2),
            free_plan_expires_at=future
        )
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/activate-subscription")

        assert resp.status_code == 200
        assert resp.json()["status"] == "already_active"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_403_when_free_plan_expired(self, mock_db):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        user = make_user(
            subscription_tier=None,
            free_plan_activated_at=datetime.now(timezone.utc) - timedelta(days=8),
            free_plan_expires_at=past
        )
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/activate-subscription")

        assert resp.status_code == 403
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_returns_already_active_for_paid_tier(self, mock_db):
        user = make_user(subscription_tier="pro", free_plan_activated_at=None)
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/activate-subscription")

        assert resp.status_code == 200
        assert resp.json()["status"] == "already_active"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_sets_7_day_expiry(self, mock_db):
        user = make_user(subscription_tier=None, free_plan_activated_at=None)
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/activate-subscription")

        data = resp.json()
        activated = datetime.fromisoformat(data["activated_at"])
        expires   = datetime.fromisoformat(data["expires_at"])
        assert (expires - activated).days == 7
        app.dependency_overrides.clear()

# ─────────────────────────────────────────────────────────────────────────
# GET /free-plan-status
# ─────────────────────────────────────────────────────────────────────────

class TestFreePlanStatus:

    def _auth_override(self, user):
        from subscription.auth import get_current_user
        async def _dep():
            return user
        app.dependency_overrides[get_current_user] = _dep

    @pytest.mark.asyncio
    async def test_not_used_when_never_activated(self, mock_db):
        user = make_user(free_plan_activated_at=None)
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/free-plan-status")

        assert resp.json()["status"] == "not_used"
        assert resp.json()["eligible"] is True
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_active_when_within_expiry(self, mock_db):
        future = datetime.now(timezone.utc) + timedelta(days=3)
        user = make_user(
            subscription_tier="free",
            free_plan_activated_at=datetime.now(timezone.utc) - timedelta(days=4),
            free_plan_expires_at=future
        )
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/free-plan-status")

        assert resp.json()["status"] == "active"
        assert resp.json()["eligible"] is False
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_expired_when_past_expiry(self, mock_db):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        user = make_user(
            free_plan_activated_at=datetime.now(timezone.utc) - timedelta(days=8),
            free_plan_expires_at=past
        )
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/free-plan-status")

        assert resp.json()["status"] == "expired"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_days_remaining_present_when_active(self, mock_db):
        future = datetime.now(timezone.utc) + timedelta(days=5)
        user = make_user(
            subscription_tier="free",
            free_plan_activated_at=datetime.now(timezone.utc) - timedelta(days=2),
            free_plan_expires_at=future
        )
        self._auth_override(user)
        app.dependency_overrides[get_db] = _override_db(mock_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/free-plan-status")

        assert "days_remaining" in resp.json()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────
# POST /webhooks/stripe
# ─────────────────────────────────────────────────────────────────────────

class TestStripeWebhook:

    def _post_webhook(self, client, event_type, data_object):
        event = {"type": event_type, "data": {"object": data_object}}
        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event):
            return client.post(
                "/webhooks/stripe",
                content=b"payload",
                headers={"stripe-signature": "sig_test"}
            )

    @pytest.mark.asyncio
    async def test_returns_400_on_invalid_signature(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)

        with patch("subscription.main.StripeClient.get_webhook_event",
                   side_effect=Exception("Invalid signature")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"bad",
                                         headers={"stripe-signature": "bad_sig"})

        assert resp.status_code == 400
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_checkout_session_completed_creates_subscription(self, mock_db):
        customer = make_customer()
        price    = make_price()
        plan     = make_plan()
        app.dependency_overrides[get_db] = _override_db(mock_db)

        uid = str(uuid4())
        session_obj = {
            "id": "cs_test", "customer": "cus_abc",
            "subscription": "sub_abc", "payment_status": "paid",
            "metadata": {"user_id": uid}
        }
        event = {"type": "checkout.session.completed", "data": {"object": session_obj}}

        stripe_sub = {
            "id": "sub_abc",
            "items": {"data": [{"price": {"id": "price_abc"}}]},
            "current_period_start": 1700000000,
            "current_period_end":   1702592000,
        }

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        exec_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = exec_result

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.get_subscription_by_stripe_id", new=AsyncMock(return_value=None)), \
             patch("subscription.main.StripeClient.retrieve_subscription", return_value=stripe_sub), \
             patch("subscription.main.get_plan_price_by_stripe_id",  new=AsyncMock(return_value=price)), \
             patch("subscription.main.get_customer",                 new=AsyncMock(return_value=customer)), \
             patch("subscription.main.create_subscription",          new=AsyncMock()), \
             patch("subscription.main.get_plan",                     new=AsyncMock(return_value=plan)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_checkout_session_skips_duplicate_subscription(self, mock_db):
        existing_sub = make_subscription()
        app.dependency_overrides[get_db] = _override_db(mock_db)

        session_obj = {
            "customer": "cus_abc", "subscription": "sub_abc",
            "payment_status": "paid", "metadata": {"user_id": str(uuid4())}
        }
        event = {"type": "checkout.session.completed", "data": {"object": session_obj}}

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.get_subscription_by_stripe_id",
                   new=AsyncMock(return_value=existing_sub)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        assert "already exists" in resp.json().get("message", "")
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invoice_payment_succeeded_renews_subscription(self, mock_db):
        sub = make_subscription()
        app.dependency_overrides[get_db] = _override_db(mock_db)

        stripe_sub = {
            "id": "sub_abc",
            "current_period_start": 1700000000,
            "current_period_end":   1702592000,
        }
        invoice_obj = {"subscription": "sub_abc"}
        event = {"type": "invoice.payment_succeeded", "data": {"object": invoice_obj}}

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.StripeClient.retrieve_subscription", return_value=stripe_sub), \
             patch("subscription.main.get_subscription_by_stripe_id", new=AsyncMock(return_value=sub)), \
             patch("subscription.main.update_subscription",           new=AsyncMock(return_value=sub)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_subscription_updated_schedules_cancel(self, mock_db):
        sub = make_subscription()
        app.dependency_overrides[get_db] = _override_db(mock_db)

        sub_obj = {
            "id": "sub_abc", "cancel_at_period_end": True,
            "status": "active", "cancel_at": 1702592000
        }
        event = {"type": "customer.subscription.updated", "data": {"object": sub_obj}}

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.get_subscription_by_stripe_id", new=AsyncMock(return_value=sub)), \
             patch("subscription.main.update_subscription",           new=AsyncMock(return_value=sub)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_subscription_deleted_cancels_and_resets_tier(self, mock_db):
        sub = make_subscription()
        app.dependency_overrides[get_db] = _override_db(mock_db)

        sub_obj = {"id": "sub_abc", "canceled_at": 1700000000}
        event = {"type": "customer.subscription.deleted", "data": {"object": sub_obj}}

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = exec_result

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.get_subscription_by_stripe_id", new=AsyncMock(return_value=sub)), \
             patch("subscription.main.update_subscription",           new=AsyncMock(return_value=sub)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_product_created_event(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)
        product_obj = {"id": "prod_abc", "name": "Pro", "active": True,
                       "description": "Pro plan", "metadata": {}}
        event = {"type": "product.created", "data": {"object": product_obj}}

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.create_plan_from_stripe", new=AsyncMock(return_value=make_plan())):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_product_deleted_event(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)
        product_obj = {"id": "prod_abc", "name": "Pro"}
        event = {"type": "product.deleted", "data": {"object": product_obj}}

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.delete_plan_from_stripe", new=AsyncMock(return_value=None)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_price_created_event(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)
        price_obj = {"id": "price_abc", "product": "prod_abc", "active": True,
                     "currency": "inr", "unit_amount": 49900,
                     "recurring": {"interval": "month"}}
        event = {"type": "price.created", "data": {"object": price_obj}}

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.create_plan_price_from_stripe", new=AsyncMock(return_value=make_price())):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_price_deleted_event(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)
        price_obj = {"id": "price_abc"}
        event = {"type": "price.deleted", "data": {"object": price_obj}}

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event), \
             patch("subscription.main.delete_plan_price_from_stripe", new=AsyncMock(return_value=None)):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unhandled_event_type_returns_ok(self, mock_db):
        app.dependency_overrides[get_db] = _override_db(mock_db)
        event = {"type": "payment_intent.created", "data": {"object": {}}}

        with patch("subscription.main.StripeClient.get_webhook_event", return_value=event):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/webhooks/stripe", content=b"payload",
                                         headers={"stripe-signature": "sig_test"})

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        app.dependency_overrides.clear()
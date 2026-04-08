"""
tests/unit/subscription/test_schema.py
Pydantic schema validation tests — no DB/network.
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from pydantic import ValidationError


class TestPlanPriceOut:

    def _valid(self, **ov):
        d = {"id": uuid4(), "billing_period": "monthly", "currency": "INR",
             "amount": 499, "stripe_price_id": "price_abc", "is_active": True}
        d.update(ov)
        return d

    def test_valid_data_passes(self):
        from subscription.schema import PlanPriceOut
        assert PlanPriceOut(**self._valid()).billing_period == "monthly"

    def test_id_is_uuid(self):
        from subscription.schema import PlanPriceOut
        assert isinstance(PlanPriceOut(**self._valid()).id, UUID)

    def test_missing_stripe_price_id_raises(self):
        from subscription.schema import PlanPriceOut
        d = self._valid()
        del d["stripe_price_id"]
        with pytest.raises(ValidationError):
            PlanPriceOut(**d)


class TestPlanOut:

    def _valid(self, **ov):
        d = {"id": uuid4(), "name": "Pro", "description": "Pro plan",
             "features_json": {}, "is_active": True, "prices": []}
        d.update(ov)
        return d

    def test_valid_data_passes(self):
        from subscription.schema import PlanOut
        assert PlanOut(**self._valid()).name == "Pro"

    def test_description_is_optional(self):
        from subscription.schema import PlanOut
        d = self._valid()
        del d["description"]
        assert PlanOut(**d).description is None

    def test_prices_defaults_to_empty_list(self):
        from subscription.schema import PlanOut
        d = self._valid()
        del d["prices"]
        assert PlanOut(**d).prices == []

    def test_missing_name_raises(self):
        from subscription.schema import PlanOut
        d = self._valid()
        del d["name"]
        with pytest.raises(ValidationError):
            PlanOut(**d)


class TestCheckoutSessionRequest:

    def test_valid_monthly(self):
        from subscription.schema import CheckoutSessionRequest
        obj = CheckoutSessionRequest(user_id=uuid4(), plan_id=uuid4(), billing_period="monthly")
        assert obj.billing_period == "monthly"

    def test_valid_yearly(self):
        from subscription.schema import CheckoutSessionRequest
        obj = CheckoutSessionRequest(user_id=uuid4(), plan_id=uuid4(), billing_period="yearly")
        assert obj.billing_period == "yearly"

    def test_invalid_billing_period_raises(self):
        from subscription.schema import CheckoutSessionRequest
        with pytest.raises(ValidationError):
            CheckoutSessionRequest(user_id=uuid4(), plan_id=uuid4(), billing_period="weekly")

    def test_missing_user_id_raises(self):
        from subscription.schema import CheckoutSessionRequest
        with pytest.raises(ValidationError):
            CheckoutSessionRequest(plan_id=uuid4(), billing_period="monthly")


class TestSubscriptionOut:

    def _valid(self, **ov):
        now = datetime.now(timezone.utc)
        d = {"id": uuid4(), "customer_id": uuid4(), "plan_id": uuid4(),
             "status": "active", "stripe_subscription_id": "sub_abc",
             "current_period_start": now, "current_period_end": now, "updated_at": now}
        d.update(ov)
        return d

    def test_valid_data_passes(self):
        from subscription.schema import SubscriptionOut
        assert SubscriptionOut(**self._valid()).status == "active"

    def test_optional_fields_default_to_none(self):
        from subscription.schema import SubscriptionOut
        obj = SubscriptionOut(**self._valid())
        assert obj.cancel_at is None
        assert obj.cancelled_at is None
        assert obj.ended_at is None
        assert obj.trial_ends_at is None

    def test_missing_status_raises(self):
        from subscription.schema import SubscriptionOut
        d = self._valid()
        del d["status"]
        with pytest.raises(ValidationError):
            SubscriptionOut(**d)


class TestCancelSubscriptionRequest:

    def test_defaults_to_true(self):
        from subscription.schema import CancelSubscriptionRequest
        assert CancelSubscriptionRequest().cancel_at_period_end is True

    def test_accepts_false(self):
        from subscription.schema import CancelSubscriptionRequest
        assert CancelSubscriptionRequest(cancel_at_period_end=False).cancel_at_period_end is False


class TestCustomerPortalSchemas:

    def test_portal_request_valid(self):
        from subscription.schema import CustomerPortalRequest
        obj = CustomerPortalRequest(user_id=str(uuid4()))
        assert obj.user_id

    def test_portal_request_missing_user_id_raises(self):
        from subscription.schema import CustomerPortalRequest
        with pytest.raises(ValidationError):
            CustomerPortalRequest()

    def test_portal_response_url(self):
        from subscription.schema import CustomerPortalResponse
        obj = CustomerPortalResponse(url="https://billing.stripe.com/session/abc")
        assert "billing.stripe.com" in obj.url
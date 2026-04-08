"""
tests/unit/subscription/test_stripe_client.py
All stripe.* SDK calls are patched — no real network calls.
"""
import pytest
import stripe as stripe_lib
from unittest.mock import MagicMock, patch
from stripe_client import StripeClient


class TestCreateCustomer:

    def test_returns_customer_id(self):
        mock_customer = MagicMock()
        mock_customer.id = "cus_abc123"
        with patch("stripe_client.stripe.Customer.create", return_value=mock_customer):
            assert StripeClient.create_customer("user-uuid-1") == "cus_abc123"

    def test_passes_user_id_as_metadata(self):
        mock_customer = MagicMock()
        mock_customer.id = "cus_abc123"
        with patch("stripe_client.stripe.Customer.create", return_value=mock_customer) as m:
            StripeClient.create_customer("user-uuid-1")
        assert m.call_args[1]["metadata"]["user_id"] == "user-uuid-1"

    def test_passes_email_when_provided(self):
        mock_customer = MagicMock()
        mock_customer.id = "cus_abc123"
        with patch("stripe_client.stripe.Customer.create", return_value=mock_customer) as m:
            StripeClient.create_customer("user-uuid-1", email="user@example.com")
        assert m.call_args[1]["email"] == "user@example.com"

    def test_no_email_field_when_email_omitted(self):
        mock_customer = MagicMock()
        mock_customer.id = "cus_abc123"
        with patch("stripe_client.stripe.Customer.create", return_value=mock_customer) as m:
            StripeClient.create_customer("user-uuid-1")
        assert "email" not in m.call_args[1]


class TestCreateCheckoutSession:

    def _mock_session(self, url="https://checkout.stripe.com/pay/cs_test"):
        s = MagicMock()
        s.url = url
        return s

    def test_returns_session_url(self):
        with patch("stripe_client.stripe.checkout.Session.create",
                   return_value=self._mock_session()):
            result = StripeClient.create_checkout_session(
                "cus_abc", "price_abc",
                "https://example.com/success", "https://example.com/cancel"
            )
        assert "checkout.stripe.com" in result

    def test_success_url_appends_session_id_placeholder(self):
        with patch("stripe_client.stripe.checkout.Session.create",
                   return_value=self._mock_session()) as m:
            StripeClient.create_checkout_session(
                "cus_abc", "price_abc",
                "https://example.com/success", "https://example.com/cancel"
            )
        assert "{CHECKOUT_SESSION_ID}" in m.call_args[1]["success_url"]

    def test_mode_defaults_to_subscription(self):
        with patch("stripe_client.stripe.checkout.Session.create",
                   return_value=self._mock_session()) as m:
            StripeClient.create_checkout_session(
                "cus_abc", "price_abc",
                "https://example.com/success", "https://example.com/cancel"
            )
        assert m.call_args[1]["mode"] == "subscription"

    def test_metadata_passed_when_provided(self):
        with patch("stripe_client.stripe.checkout.Session.create",
                   return_value=self._mock_session()) as m:
            StripeClient.create_checkout_session(
                "cus_abc", "price_abc",
                "https://example.com/success", "https://example.com/cancel",
                metadata={"user_id": "uid-123"}
            )
        assert m.call_args[1]["metadata"]["user_id"] == "uid-123"

    def test_no_metadata_key_when_not_provided(self):
        with patch("stripe_client.stripe.checkout.Session.create",
                   return_value=self._mock_session()) as m:
            StripeClient.create_checkout_session(
                "cus_abc", "price_abc",
                "https://example.com/success", "https://example.com/cancel"
            )
        assert "metadata" not in m.call_args[1]

    def test_price_id_in_line_items(self):
        with patch("stripe_client.stripe.checkout.Session.create",
                   return_value=self._mock_session()) as m:
            StripeClient.create_checkout_session(
                "cus_abc", "price_xyz",
                "https://example.com/success", "https://example.com/cancel"
            )
        assert m.call_args[1]["line_items"][0]["price"] == "price_xyz"

    def test_quantity_is_1(self):
        with patch("stripe_client.stripe.checkout.Session.create",
                   return_value=self._mock_session()) as m:
            StripeClient.create_checkout_session(
                "cus_abc", "price_abc",
                "https://example.com/success", "https://example.com/cancel"
            )
        assert m.call_args[1]["line_items"][0]["quantity"] == 1

    def test_payment_method_includes_card(self):
        with patch("stripe_client.stripe.checkout.Session.create",
                   return_value=self._mock_session()) as m:
            StripeClient.create_checkout_session(
                "cus_abc", "price_abc",
                "https://example.com/success", "https://example.com/cancel"
            )
        assert "card" in m.call_args[1]["payment_method_types"]


class TestCancelSubscription:

    def test_calls_stripe_modify_with_defaults(self):
        with patch("stripe_client.stripe.Subscription.modify") as m:
            StripeClient.cancel_subscription("sub_abc")
        m.assert_called_once_with("sub_abc", cancel_at_period_end=True)

    def test_cancel_at_period_end_false(self):
        with patch("stripe_client.stripe.Subscription.modify") as m:
            StripeClient.cancel_subscription("sub_abc", cancel_at_period_end=False)
        assert m.call_args[1]["cancel_at_period_end"] is False

    def test_returns_none(self):
        with patch("stripe_client.stripe.Subscription.modify"):
            assert StripeClient.cancel_subscription("sub_abc") is None


class TestRetrieveSubscription:

    def test_returns_subscription_object(self):
        mock_sub = MagicMock()
        with patch("stripe_client.stripe.Subscription.retrieve", return_value=mock_sub):
            assert StripeClient.retrieve_subscription("sub_abc") is mock_sub

    def test_passes_correct_sub_id(self):
        mock_sub = MagicMock()
        with patch("stripe_client.stripe.Subscription.retrieve", return_value=mock_sub) as m:
            StripeClient.retrieve_subscription("sub_xyz")
        m.assert_called_once_with("sub_xyz")


class TestGetWebhookEvent:

    def test_returns_event_on_valid_payload(self):
        mock_event = {"type": "checkout.session.completed"}
        with patch("stripe_client.stripe.Webhook.construct_event", return_value=mock_event):
            result = StripeClient.get_webhook_event(b"payload", "sig", "whsec_secret")
        assert result["type"] == "checkout.session.completed"

    def test_raises_on_invalid_payload(self):
        with patch("stripe_client.stripe.Webhook.construct_event",
                   side_effect=ValueError("Invalid")):
            with pytest.raises(Exception, match="Invalid payload"):
                StripeClient.get_webhook_event(b"bad", "sig", "whsec")

    def test_raises_on_invalid_signature(self):
        with patch("stripe_client.stripe.Webhook.construct_event",
                   side_effect=stripe_lib.error.SignatureVerificationError("fail", "sig")):
            with pytest.raises(Exception, match="Invalid signature"):
                StripeClient.get_webhook_event(b"payload", "bad_sig", "whsec")

    def test_passes_all_three_args_to_stripe(self):
        mock_event = {"type": "ping"}
        with patch("stripe_client.stripe.Webhook.construct_event",
                   return_value=mock_event) as m:
            StripeClient.get_webhook_event(b"payload", "sig_header", "whsec_secret")
        m.assert_called_once_with(b"payload", "sig_header", "whsec_secret")


class TestParseCheckoutSession:

    def _session(self, customer="cus_abc", subscription="sub_abc",
                 user_id="uid-123", payment_status="paid"):
        return {
            "customer": customer,
            "subscription": subscription,
            "metadata": {"user_id": user_id},
            "payment_status": payment_status,
        }

    def test_returns_customer_id(self):
        assert StripeClient.parse_checkout_session(self._session())["customer_id"] == "cus_abc"

    def test_returns_subscription_id(self):
        assert StripeClient.parse_checkout_session(self._session())["subscription_id"] == "sub_abc"

    def test_returns_user_id_from_metadata(self):
        assert StripeClient.parse_checkout_session(self._session())["user_id"] == "uid-123"

    def test_returns_payment_status(self):
        assert StripeClient.parse_checkout_session(self._session())["payment_status"] == "paid"

    def test_none_subscription_when_missing(self):
        s = self._session()
        s.pop("subscription")
        assert StripeClient.parse_checkout_session(s)["subscription_id"] is None

    def test_none_user_id_when_metadata_key_missing(self):
        s = {"customer": "cus_abc", "subscription": "sub_abc",
             "metadata": {}, "payment_status": "paid"}
        assert StripeClient.parse_checkout_session(s)["user_id"] is None


class TestGetPaymentMethods:

    def _mock_pm(self, pm_id, brand, last4, exp_month, exp_year):
        pm = MagicMock()
        pm.id = pm_id
        pm.card.brand = brand
        pm.card.last4 = last4
        pm.card.exp_month = exp_month
        pm.card.exp_year = exp_year
        return pm

    def test_returns_list_of_payment_methods(self):
        pm = self._mock_pm("pm_abc", "visa", "4242", 12, 2027)
        pm_list = MagicMock()
        pm_list.data = [pm]
        customer = MagicMock()
        customer.invoice_settings.default_payment_method = "pm_abc"
        with patch("stripe_client.stripe.PaymentMethod.list", return_value=pm_list), \
             patch("stripe_client.stripe.Customer.retrieve", return_value=customer):
            result = StripeClient.get_payment_methods("cus_abc")
        assert len(result) == 1
        assert result[0]["id"] == "pm_abc"

    def test_is_default_true_for_default_pm(self):
        pm = self._mock_pm("pm_default", "visa", "4242", 12, 2027)
        pm_list = MagicMock()
        pm_list.data = [pm]
        customer = MagicMock()
        customer.invoice_settings.default_payment_method = "pm_default"
        with patch("stripe_client.stripe.PaymentMethod.list", return_value=pm_list), \
             patch("stripe_client.stripe.Customer.retrieve", return_value=customer):
            assert StripeClient.get_payment_methods("cus_abc")[0]["is_default"] is True

    def test_is_default_false_for_non_default(self):
        pm = self._mock_pm("pm_other", "mastercard", "5555", 6, 2026)
        pm_list = MagicMock()
        pm_list.data = [pm]
        customer = MagicMock()
        customer.invoice_settings.default_payment_method = "pm_different"
        with patch("stripe_client.stripe.PaymentMethod.list", return_value=pm_list), \
             patch("stripe_client.stripe.Customer.retrieve", return_value=customer):
            assert StripeClient.get_payment_methods("cus_abc")[0]["is_default"] is False

    def test_returns_empty_list_on_exception(self):
        with patch("stripe_client.stripe.PaymentMethod.list",
                   side_effect=Exception("Stripe error")):
            assert StripeClient.get_payment_methods("cus_abc") == []

    def test_all_fields_present(self):
        pm = self._mock_pm("pm_abc", "visa", "4242", 12, 2027)
        pm_list = MagicMock()
        pm_list.data = [pm]
        customer = MagicMock()
        customer.invoice_settings.default_payment_method = None
        with patch("stripe_client.stripe.PaymentMethod.list", return_value=pm_list), \
             patch("stripe_client.stripe.Customer.retrieve", return_value=customer):
            result = StripeClient.get_payment_methods("cus_abc")
        assert {"id", "brand", "last4", "exp_month", "exp_year", "is_default"}.issubset(result[0])


class TestCreateCustomerPortalSession:

    def test_returns_portal_url(self):
        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/session/abc"
        with patch("stripe_client.stripe.billing_portal.Session.create",
                   return_value=mock_session):
            result = StripeClient.create_customer_portal_session(
                "cus_abc", "https://example.com/return"
            )
        assert result == "https://billing.stripe.com/session/abc"

    def test_passes_correct_customer_id(self):
        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/session/abc"
        with patch("stripe_client.stripe.billing_portal.Session.create",
                   return_value=mock_session) as m:
            StripeClient.create_customer_portal_session("cus_xyz", "https://example.com")
        assert m.call_args[1]["customer"] == "cus_xyz"

    def test_passes_return_url(self):
        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/session/abc"
        with patch("stripe_client.stripe.billing_portal.Session.create",
                   return_value=mock_session) as m:
            StripeClient.create_customer_portal_session(
                "cus_abc", "https://example.com/dashboard"
            )
        assert m.call_args[1]["return_url"] == "https://example.com/dashboard"

    def test_raises_stripe_error_on_failure(self):
        with patch("stripe_client.stripe.billing_portal.Session.create",
                   side_effect=stripe_lib.error.StripeError("error")):
            with pytest.raises(stripe_lib.error.StripeError):
                StripeClient.create_customer_portal_session("cus_abc", "https://example.com")

    def test_raises_on_generic_exception(self):
        with patch("stripe_client.stripe.billing_portal.Session.create",
                   side_effect=Exception("unexpected")):
            with pytest.raises(Exception):
                StripeClient.create_customer_portal_session("cus_abc", "https://example.com")
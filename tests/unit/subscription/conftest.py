"""
tests/unit/subscription/conftest.py
Bootstraps sys.path + shared model factories + mock_db fixture.
"""
import os
import sys
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest

_here      = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_here, "../../.."))
_svc_root  = os.path.join(_repo_root, "subscription")

if _svc_root not in sys.path:
    sys.path.insert(0, _svc_root)

os.environ.setdefault("DATABASE_URL",            "postgresql://user:pass@localhost/testdb")
os.environ.setdefault("JWT_SECRET_KEY",          "test-secret-key-subscription-32b!")
os.environ.setdefault("JWT_ALGORITHM",           "HS256")
os.environ.setdefault("STRIPE_SECRET_KEY",       "sk_test_fake")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET",   "whsec_fake")


# ── factories ─────────────────────────────────────────────────────────────

def make_plan(name="Pro", active=True):
    from subscription.models import Plan
    p = Plan()
    p.id                = uuid4()
    p.name              = name
    p.description       = f"{name} plan"
    p.features_json     = {"feature_a": True}
    p.stripe_product_id = f"prod_{name.lower()}"
    p.is_active         = active
    return p


def make_price(plan_id=None, billing_period="monthly", amount=499,
               stripe_price_id="price_test_monthly", active=True):
    from subscription.models import PlanPrice
    pp = PlanPrice()
    pp.id              = uuid4()
    pp.plan_id         = plan_id or uuid4()
    pp.billing_period  = billing_period
    pp.currency        = "INR"
    pp.amount          = amount
    pp.stripe_price_id = stripe_price_id
    pp.is_active       = active
    return pp


def make_customer(user_id=None):
    from subscription.models import Customer
    c = Customer()
    c.id                 = uuid4()
    c.user_id            = user_id or uuid4()
    c.stripe_customer_id = "cus_test_fake"
    return c


def make_subscription(customer_id=None, plan_id=None, status="active",
                      stripe_sub_id="sub_test_fake"):
    from subscription.models import Subscription
    s = Subscription()
    s.id                     = uuid4()
    s.customer_id            = customer_id or uuid4()
    s.plan_id                = plan_id or uuid4()
    s.status                 = status
    s.stripe_subscription_id = stripe_sub_id
    now = datetime.now(timezone.utc)
    s.current_period_start   = now
    s.current_period_end     = now + timedelta(days=30)
    s.cancel_at              = None
    s.cancelled_at           = None
    s.ended_at               = None
    s.trial_ends_at          = None
    s.updated_at             = now
    return s


def make_user(subscription_tier=None, free_plan_activated_at=None,
              free_plan_expires_at=None):
    from subscription.models import User
    u = User()
    u.user_id                = uuid4()
    u.email                  = "user@example.com"
    u.name                   = "Test User"
    u.subscription_tier      = subscription_tier
    u.free_plan_activated_at = free_plan_activated_at
    u.free_plan_expires_at   = free_plan_expires_at
    return u


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit   = AsyncMock()
    db.refresh  = AsyncMock()
    db.rollback = AsyncMock()
    db.execute  = AsyncMock()
    db.add      = MagicMock()
    return db
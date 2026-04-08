# tests/unit/subscription/conftest.py

import os
import sys
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest

_here      = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_here, "../../.."))

# Only repo root on sys.path — subscription/ must NOT be added
# (adding it causes models to load twice → duplicate SQLAlchemy mapper error)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Defensively strip subscription/ if pytest or another plugin added it
_svc_root = os.path.join(_repo_root, "subscription")
while _svc_root in sys.path:
    sys.path.remove(_svc_root)

os.environ.setdefault("DATABASE_URL",          "postgresql://user:pass@localhost/testdb")
os.environ.setdefault("JWT_SECRET_KEY",        "test-secret-key-subscription-32b!")
os.environ.setdefault("JWT_ALGORITHM",         "HS256")
os.environ.setdefault("STRIPE_SECRET_KEY",     "sk_test_fake")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_fake")

# ── STEP 1: alias bare names BEFORE any subscription module is imported ───
# crud.py line 4:  `from models import ...`   fires during `import subscription.crud`
# auth.py line 11: `from db import get_db`    fires during `import subscription.auth`
# We must put the real modules into sys.modules["db"] / sys.modules["models"]
# BEFORE those dotted imports trigger the source file to execute.

import subscription.db as _db          # db.py has no internal flat imports → safe first
sys.modules["db"] = _db                # now `from db import ...` resolves from cache

import subscription.models as _models  # models.py only needs `db` → now resolved above
sys.modules["models"] = _models

import subscription.schema as _schema  # schema.py has no internal flat imports
sys.modules["schema"] = _schema

# crud.py needs models + schema — both aliased above ✓
import subscription.crud as _crud
sys.modules["crud"] = _crud

# auth.py needs db + models — both aliased above ✓
import subscription.auth as _auth
sys.modules["auth"] = _auth

# stripe_client.py has no internal flat imports
import subscription.stripe_client as _stripe_client
sys.modules["stripe_client"] = _stripe_client

# ── STEP 2: pull model classes (single registry entry guaranteed) ─────────
from subscription.models import Plan, PlanPrice, Customer, Subscription, User


# ── Factories ─────────────────────────────────────────────────────────────

def make_plan(name="Pro", active=True):
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
    c = Customer()
    c.id                 = uuid4()
    c.user_id            = user_id or uuid4()
    c.stripe_customer_id = "cus_test_fake"
    return c


def make_subscription(customer_id=None, plan_id=None, status="active",
                      stripe_sub_id="sub_test_fake"):
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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from sqlalchemy.orm import selectinload
from models import Customer, Subscription, Plan, PlanPrice, User
from uuid import UUID
from datetime import datetime, timezone
import uuid


# ========== CUSTOMER ==========

async def get_customer(db: AsyncSession, user_id: UUID):
    result = await db.execute(
        select(Customer).where(Customer.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_customer(db: AsyncSession, user_id: UUID, stripe_customer_id: str):
    await db.execute(text("""
        INSERT INTO stud_hub_schema.customers (user_id, stripe_customer_id) 
        VALUES (:user_id, :stripe_customer_id)
        ON CONFLICT (stripe_customer_id) DO NOTHING
    """), {
        "user_id": user_id,
        "stripe_customer_id": stripe_customer_id
    })
    await db.commit()
    return await get_customer(db, user_id)


# ========== PLANS ==========

async def get_plan(db: AsyncSession, plan_id: UUID):
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    return result.scalars().first()


async def get_all_plans(db: AsyncSession):
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.prices))
        .where(Plan.is_active == True)
    )
    return result.scalars().all()


# ========== PLAN PRICES ==========

async def get_plan_price(db: AsyncSession, plan_id: UUID, billing_period: str):
    result = await db.execute(
        select(PlanPrice)
        .where(and_(
            PlanPrice.plan_id == plan_id,
            PlanPrice.billing_period == billing_period,
            PlanPrice.is_active == True
        ))
    )
    return result.scalar_one_or_none()


async def get_plan_price_by_stripe_id(db: AsyncSession, stripe_price_id: str):
    result = await db.execute(
        select(PlanPrice).where(PlanPrice.stripe_price_id == stripe_price_id)
    )
    return result.scalar_one_or_none()


# ========== SUBSCRIPTIONS ==========

async def get_user_subscription(db: AsyncSession, user_id: UUID):
    result = await db.execute(
        select(Subscription, Plan.name.label("plan_name"))
        .join(Customer, Customer.id == Subscription.customer_id)
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(and_(
            Customer.user_id == user_id,
            Subscription.status == "active"
        ))
    )
    row = result.first()
    if not row:
        return None
    sub, plan_name = row
    sub.plan_name = plan_name

    # ── Real-time expiry guard ─────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    if sub.current_period_end < now:
        # Subscription technically active in DB but period has lapsed —
        # lock it immediately without waiting for the scheduler
        await db.execute(
            text("""
                UPDATE stud_hub_schema.subscriptions
                SET status = 'expired', ended_at = :now
                WHERE id = :sub_id
            """),
            {"now": now, "sub_id": str(sub.id)}
        )
        await db.execute(
            text("""
                UPDATE stud_hub_schema.users
                SET subscription_tier = NULL
                WHERE user_id = (
                    SELECT user_id FROM stud_hub_schema.customers
                    WHERE id = :customer_id
                )
            """),
            {"customer_id": str(sub.customer_id)}
        )
        await db.commit()
        return None  # treat as no active subscription

    return sub


async def get_subscription_by_stripe_id(db: AsyncSession, stripe_sub_id: str):
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    return result.scalar_one_or_none()


async def create_subscription(
    db: AsyncSession,
    customer_id: UUID,
    plan_id: UUID,
    stripe_sub_id: str,
    period_start: datetime,
    period_end: datetime,
    status: str = "active"
):
    sub = Subscription(
        customer_id=customer_id,
        plan_id=plan_id,
        status=status,
        stripe_subscription_id=stripe_sub_id,
        current_period_start=period_start,
        current_period_end=period_end
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def update_subscription(
    db: AsyncSession,
    subscription_id: UUID,
    **fields
):
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        for key, value in fields.items():
            setattr(subscription, key, value)
        await db.commit()
        await db.refresh(subscription)

    return subscription

async def has_used_free_plan(db: AsyncSession, customer_id: UUID) -> bool:
    """Check if customer has ever had a free plan subscription (active or cancelled)."""
    result = await db.execute(
        select(Subscription)
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(
            and_(
                Subscription.customer_id == customer_id,
                Plan.name.ilike("free")   # case-insensitive match
            )
        )
    )
    return result.scalar_one_or_none() is not None


# ========== STRIPE SYNC (Webhook Handlers) ==========

def _get_billing_period(stripe_price: dict) -> str:
    """Map Stripe recurring interval to billing period string."""
    recurring = stripe_price.get('recurring')
    if not recurring:
        return 'one_time'
    interval = recurring['interval']
    count = recurring.get('interval_count', 1)
    if interval == 'month' and count == 1:
        return 'monthly'
    if interval == 'year' and count == 1:
        return 'yearly'
    return f"{count}_{interval}"    # e.g. "7_day" for free plan


async def create_plan_from_stripe(db: AsyncSession, stripe_product: dict):
    result = await db.execute(
        select(Plan).where(Plan.stripe_product_id == stripe_product['id'])
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"⚠️ Plan already exists: {stripe_product['name']}")
        return existing

    plan = Plan(
        id=uuid.uuid4(),
        name=stripe_product['name'],
        description=stripe_product.get('description'),
        stripe_product_id=stripe_product['id'],
        features_json=stripe_product.get('metadata', {}),
        is_active=stripe_product['active']
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def update_plan_from_stripe(db: AsyncSession, stripe_product: dict):
    result = await db.execute(
        select(Plan).where(Plan.stripe_product_id == stripe_product['id'])
    )
    plan = result.scalar_one_or_none()
    if not plan:
        return await create_plan_from_stripe(db, stripe_product)

    plan.name = stripe_product['name']
    plan.description = stripe_product.get('description')
    plan.is_active = stripe_product['active']
    plan.features_json = stripe_product.get('metadata', {})

    await db.commit()
    await db.refresh(plan)
    return plan


async def delete_plan_from_stripe(db: AsyncSession, stripe_product_id: str):
    result = await db.execute(
        select(Plan).where(Plan.stripe_product_id == stripe_product_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        print(f"⚠️ Plan not found for product: {stripe_product_id}")
        return

    plan.is_active = False
    await db.commit()
    await db.refresh(plan)
    print(f" Plan soft-deleted: {plan.name}")
    return plan


async def create_plan_price_from_stripe(db: AsyncSession, stripe_price: dict):
    result = await db.execute(
        select(PlanPrice).where(PlanPrice.stripe_price_id == stripe_price['id'])
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"⚠️ Price already exists: {stripe_price['id']}")
        return existing

    result = await db.execute(
        select(Plan).where(Plan.stripe_product_id == stripe_price['product'])
    )
    plan = result.scalar_one_or_none()
    if not plan:
        print(f"❌ Plan not found for product: {stripe_price['product']}")
        return None

    plan_price = PlanPrice(
        id=uuid.uuid4(),
        plan_id=plan.id,
        billing_period=_get_billing_period(stripe_price),  # ✅ fixed mapping
        currency=stripe_price['currency'].upper(),
        amount=stripe_price['unit_amount'] // 100,
        stripe_price_id=stripe_price['id'],
        is_active=stripe_price['active']
    )
    db.add(plan_price)
    await db.commit()
    await db.refresh(plan_price)
    return plan_price


async def update_plan_price_from_stripe(db: AsyncSession, stripe_price: dict):
    result = await db.execute(
        select(PlanPrice).where(PlanPrice.stripe_price_id == stripe_price['id'])
    )
    plan_price = result.scalar_one_or_none()
    if not plan_price:
        return await create_plan_price_from_stripe(db, stripe_price)

    plan_price.is_active = stripe_price['active']
    await db.commit()
    await db.refresh(plan_price)
    return plan_price


async def delete_plan_price_from_stripe(db: AsyncSession, stripe_price_id: str):
    result = await db.execute(
        select(PlanPrice).where(PlanPrice.stripe_price_id == stripe_price_id)
    )
    plan_price = result.scalar_one_or_none()
    if not plan_price:
        print(f"⚠️ Price not found: {stripe_price_id}")
        return

    plan_price.is_active = False
    await db.commit()
    await db.refresh(plan_price)
    print(f"✅ Price soft-deleted: {stripe_price_id}")
    return plan_price

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from models import Customer, Subscription, Plan, PlanPrice
from schema import CheckoutSessionRequest
from uuid import UUID
from datetime import datetime

async def get_customer(db: AsyncSession, user_id: UUID):
    result = await db.execute(
        select(Customer).where(Customer.user_id == user_id)
    )
    return result.scalar_one_or_none()

from sqlalchemy import text

async def create_customer(db: AsyncSession, user_id: UUID, stripe_customer_id: str):
    # Raw SQL - no FK validation issues
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

async def get_user_subscription(db: AsyncSession, user_id: UUID):
    result = await db.execute(
        select(Subscription)
        .join(Customer)
        .where(and_(
            Customer.user_id == user_id,
            Subscription.status == "active"
        ))
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

# Add this to existing async CRUD
async def get_plan_price_by_stripe_id(db: AsyncSession, stripe_price_id: str):
    result = await db.execute(
        select(PlanPrice).where(PlanPrice.stripe_price_id == stripe_price_id)
    )
    return result.scalar_one_or_none()

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


async def get_subscription_by_stripe_id(db: AsyncSession, stripe_sub_id: str):
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    return result.scalar_one_or_none()


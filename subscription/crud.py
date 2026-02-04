from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from models import Customer, Subscription, Plan, PlanPrice
from schema import CheckoutSessionRequest
from uuid import UUID
from datetime import datetime
import uuid

async def get_customer(db: AsyncSession, user_id: UUID):
    result = await db.execute(
        select(Customer).where(Customer.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def get_plan(db: AsyncSession, plan_id: UUID):
    """Get plan by ID"""
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    return result.scalars().first()


async def get_all_plans(db: AsyncSession):
    """Get all active plans with their prices."""
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.prices))
        .where(Plan.is_active == True)
    )
    return result.scalars().all()


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


async def create_plan_from_stripe(db: AsyncSession, stripe_product: dict):
    """Create plan from Stripe product webhook"""
    
    # Check if already exists
    result = await db.execute(
        select(Plan).where(Plan.stripe_product_id == stripe_product['id'])
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        print(f"⚠️ Plan already exists: {stripe_product['name']}")
        return existing
    
    # Extract features from metadata
    features = stripe_product.get('metadata', {})
    
    plan = Plan(
        id=uuid.uuid4(),
        name=stripe_product['name'],
        description=stripe_product.get('description'),
        stripe_product_id=stripe_product['id'],
        features_json=features,
        is_active=stripe_product['active']
    )
    
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def update_plan_from_stripe(db: AsyncSession, stripe_product: dict):
    """Update plan from Stripe product webhook"""
    
    result = await db.execute(
        select(Plan).where(Plan.stripe_product_id == stripe_product['id'])
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        # Create if doesn't exist
        return await create_plan_from_stripe(db, stripe_product)
    
    plan.name = stripe_product['name']
    plan.description = stripe_product.get('description')
    plan.is_active = stripe_product['active']
    plan.features_json = stripe_product.get('metadata', {})
    
    await db.commit()
    await db.refresh(plan)
    return plan


async def create_plan_price_from_stripe(db: AsyncSession, stripe_price: dict):
    """Create plan_price from Stripe price webhook"""
    
    # Check if already exists
    result = await db.execute(
        select(PlanPrice).where(PlanPrice.stripe_price_id == stripe_price['id'])
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        print(f"⚠️ Price already exists: {stripe_price['id']}")
        return existing
    
    # Find plan by product ID
    result = await db.execute(
        select(Plan).where(Plan.stripe_product_id == stripe_price['product'])
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        print(f"❌ Plan not found for product: {stripe_price['product']}")
        return None
    
    # Determine billing period
    billing_period = stripe_price['recurring']['interval'] if stripe_price['recurring'] else 'one_time'
    
    plan_price = PlanPrice(
        id=uuid.uuid4(),
        plan_id=plan.id,
        billing_period=billing_period,
        currency=stripe_price['currency'].upper(),
        amount=stripe_price['unit_amount'] // 100,  # Convert from paise to rupees
        stripe_price_id=stripe_price['id'],
        is_active=stripe_price['active']
    )
    
    db.add(plan_price)
    await db.commit()
    await db.refresh(plan_price)
    return plan_price


async def update_plan_price_from_stripe(db: AsyncSession, stripe_price: dict):
    """Update plan_price from Stripe price webhook"""
    
    result = await db.execute(
        select(PlanPrice).where(PlanPrice.stripe_price_id == stripe_price['id'])
    )
    plan_price = result.scalar_one_or_none()
    
    if not plan_price:
        # Create if doesn't exist
        return await create_plan_price_from_stripe(db, stripe_price)
    
    plan_price.is_active = stripe_price['active']
    
    await db.commit()
    await db.refresh(plan_price)
    return plan_price

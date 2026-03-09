from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import stripe
from dotenv import load_dotenv
import os
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import List
from sqlalchemy.orm import selectinload
from stripe_client import StripeClient
from crud import *
from schema import *
from db import get_db, engine
from models import Base, User
from auth import get_current_user
from email_service import send_subscription_success_email, send_subscription_expiry_email


load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
app = FastAPI(title="Subscription Service (Async)")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dev only - create tables
import asyncio
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# asyncio.create_task(init_db())

# Dependency
async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@app.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    db: AsyncSession = Depends(get_db)
):
    customer = await get_customer(db, request.user_id)
    if not customer:
        stripe_cust_id = StripeClient.create_customer(str(request.user_id))
        customer = await create_customer(db, request.user_id, stripe_cust_id)

    price = await get_plan_price(db, request.plan_id, request.billing_period)
    if not price:
        raise HTTPException(404, "Plan price not found")

    # Block free plan reuse
    plan = await get_plan(db, request.plan_id)
    if plan and plan.name.lower() == "free":
        has_used = await has_used_free_plan(db, customer.id)
        if has_used:
            raise HTTPException(
                status_code=403,
                detail="Free plan has already been used. Please upgrade to a paid plan."
            )

    url = StripeClient.create_checkout_session(
        customer.stripe_customer_id,
        price.stripe_price_id,
        request.success_url,
        request.cancel_url,
        {"user_id": str(request.user_id)}
    )
    return CheckoutSessionResponse(url=url)


# ========== CACHE CONFIGURATION ==========
PLANS_CACHE = None
CACHE_EXPIRY = None
CACHE_DURATION = timedelta(minutes=30)

def invalidate_plans_cache():
    """Clear plans cache when Stripe data changes"""
    global PLANS_CACHE, CACHE_EXPIRY
    PLANS_CACHE = None
    CACHE_EXPIRY = None
    print("🗑️ Plans cache invalidated")

async def get_cached_plans(db: AsyncSession):
    """Get plans from cache or DB"""
    global PLANS_CACHE, CACHE_EXPIRY
    
    if PLANS_CACHE and CACHE_EXPIRY and datetime.now() < CACHE_EXPIRY:
        print("📦 Serving plans from cache")
        return PLANS_CACHE
    
    print("🔄 Fetching plans from DB...")
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).options(
            selectinload(Plan.prices)
        )
    )
    plans = result.scalars().all()
    
    PLANS_CACHE = [
        {
            "id": str(plan.id),
            "name": plan.name,
            "description": plan.description,
            "features_json": plan.features_json,  #  Match schema field name
            "is_active": plan.is_active,  # Add missing field
            "stripe_product_id": plan.stripe_product_id,
            "prices": [
                {
                    "id": str(price.id),
                    "billing_period": price.billing_period,  # Match schema field name
                    "currency": price.currency,  # Match schema field name
                    "amount": float(price.amount),
                    "stripe_price_id": price.stripe_price_id,
                    "is_active": price.is_active  #  Add missing field
                }
                for price in plan.prices if price.is_active
            ]
        }
        for plan in plans
    ]
    
    CACHE_EXPIRY = datetime.now() + CACHE_DURATION
    print(f"✅ Plans cached until {CACHE_EXPIRY}")
    return PLANS_CACHE


@app.get("/plans", response_model=List[PlanOut])
async def get_plans(db: AsyncSession = Depends(get_db)):
    """Get all active plans (cached)"""
    plans = await get_cached_plans(db)
    return plans


@app.get("/subscriptions/{user_id}")
async def get_subscription_by_user_id(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get subscription by user ID — Stripe-only plans."""

    sub = await get_user_subscription(db, user_id)
    if sub:
        return {
            "type": "paid",
            "plan": sub.plan_name,
            "status": sub.status,
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at": sub.cancel_at.isoformat() if sub.cancel_at else None,
            "stripe_subscription_id": sub.stripe_subscription_id,
        }

    # No Stripe sub = no subscription at all (free plan columns removed)
    raise HTTPException(status_code=404, detail="No active subscription")



@app.get("/subscriptions/me", response_model=SubscriptionOut)
async def get_my_subscription(
    user_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    sub = await get_user_subscription(db, user_id)
    if not sub:
        raise HTTPException(404, "No active subscription")
    return sub  # TODO: join plan

@app.post("/subscriptions/{user_id}/cancel")
async def cancel_subscription(
    user_id: UUID, 
    request: CancelSubscriptionRequest, 
    db: AsyncSession = Depends(get_db)
):
    sub = await get_user_subscription(db, user_id)
    if not sub:
        raise HTTPException(404, "No active subscription")
    
    StripeClient.cancel_subscription(sub.stripe_subscription_id, request.cancel_at_period_end)
    return {"message": "Cancellation requested"}

# Async webhook
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = StripeClient.get_webhook_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Webhook signature failed")
    
    print(f"🔔 Webhook Event: {event['type']}")
    
    if event['type'] == 'checkout.session.completed':
        print(" CHECKOUT SESSION COMPLETED TRIGGERED!")
        
        session = event['data']['object']
        print(f"📦 Session ID: {session.get('id')}")
        print(f"💳 Subscription: {session.get('subscription')}")
        print(f"👤 Metadata: {session.get('metadata')}")
        
        parsed = StripeClient.parse_checkout_session(session)
        print(f"🔍 Parsed: {parsed}")
        
        if parsed['subscription_id'] and parsed['user_id']:
            print(" ENTERING IF BLOCK - Has sub_id + user_id")
            
            user_id = UUID(parsed['user_id'])
            stripe_sub_id = parsed['subscription_id']
            
            # CHECK IF SUBSCRIPTION ALREADY EXISTS
            existing_sub = await get_subscription_by_stripe_id(db, stripe_sub_id)
            if existing_sub:
                print(f"⚠️ Subscription already exists: {stripe_sub_id}")
                return {"status": "ok", "message": "Subscription already exists"}
            
            stripe_sub = StripeClient.retrieve_subscription(stripe_sub_id)
            plan_price_id = stripe_sub['items']['data'][0]['price']['id']
            print(f"🔍 Looking for price: {plan_price_id}")
            
            price = await get_plan_price_by_stripe_id(db, plan_price_id)
            print(f" Price found: {price}")
            
            customer = await get_customer(db, user_id)
            print(f"👤 Customer: {customer}")
            
            if price and customer:
                # STEP 1: Fetch plan FIRST before using it
                plan = await get_plan(db, price.plan_id)
                if not plan:
                    print(f"❌ Plan not found: {price.plan_id}")
                    return {"status": "ok"}

                # STEP 2: Create subscription in DB
                await create_subscription(
                    db,
                    customer.id,
                    price.plan_id,
                    parsed['subscription_id'],
                    datetime.fromtimestamp(stripe_sub['current_period_start']),
                    datetime.fromtimestamp(stripe_sub['current_period_end'])
                )
                print("🎉 Subscription created!")

                # STEP 3: Update subscription_tier
                from sqlalchemy import text
                await db.execute(
                    text("UPDATE stud_hub_schema.users SET subscription_tier = :tier WHERE user_id = :user_id"),
                    {"tier": plan.name.lower(), "user_id": str(user_id)}
                )
                await db.commit()
                print(f" User subscription_tier updated to: {plan.name}")

                # STEP 4: Send success email (non-blocking)
                try:
                    user_result = await db.execute(
                        text("SELECT email, name FROM stud_hub_schema.users WHERE user_id = :user_id"),
                        {"user_id": str(user_id)}
                    )
                    user_row = user_result.fetchone()
                    if user_row:
                        await send_subscription_success_email(
                            to_email=user_row.email,
                            user_name=user_row.name,
                            plan_name=plan.name,
                            amount=session.get("amount_total", 0) / 100,
                            currency=session.get("currency", "inr"),
                            expires_at=datetime.fromtimestamp(stripe_sub['current_period_end'])
                        )
                        print(f"📧 Success email sent to {user_row.email}")
                except Exception as e:
                    print(f"❌ Email send failed (non-blocking): {e}")
            else:
                print(f"❌ FAILED - price: {price}, customer: {customer}")
        else:
            print(f"❌ IF CONDITION FAILED - sub_id: {parsed.get('subscription_id')}, user_id: {parsed.get('user_id')}")

    #elif event['type'] == 'invoice.payment_succeeded':
        #pass
    
    elif event['type'] == 'invoice.payment_succeeded':
                # RENEWAL - UPDATE PERIOD
        invoice = event['data']['object']
                
        if invoice.get('subscription'):
            stripe_sub = StripeClient.retrieve_subscription(invoice['subscription'])
            db_sub = await get_subscription_by_stripe_id(db, stripe_sub['id'])
                    
            if db_sub:
                await update_subscription(
                    db,
                    db_sub.id,
                    current_period_start=datetime.fromtimestamp(stripe_sub['current_period_start']),
                    current_period_end=datetime.fromtimestamp(stripe_sub['current_period_end']),
                    status='active'
                )
                print("🔄 Subscription renewed")
            
    elif event['type'] == 'customer.subscription.updated':
                # CANCELLATION SCHEDULED OR STATUS CHANGE
        subscription = event['data']['object']
        db_sub = await get_subscription_by_stripe_id(db, subscription['id'])
                
        if db_sub:
            if subscription['cancel_at_period_end']:
                # Will cancel at period end
                await update_subscription(
                    db, 
                    db_sub.id,
                    status='active',
                    cancel_at=datetime.fromtimestamp(subscription['cancel_at'])
                )
                print(f"📅 Subscription will cancel at period end")
                    
            elif subscription['status'] == 'canceled':
                # Cancelled immediately
                await update_subscription(
                    db,
                    db_sub.id,
                    status='cancelled',
                    cancelled_at=datetime.utcnow()
                )

                # ✅ ADD THIS: Update user's subscription_tier to NULL when cancelled
                from sqlalchemy import text
                await db.execute(
                    text("UPDATE stud_hub_schema.users SET subscription_tier = NULL WHERE user_id = (SELECT user_id FROM stud_hub_schema.customers WHERE id = :customer_id)"),
                    {"customer_id": str(db_sub.customer_id)}
                )
                await db.commit()
                print("❌ Subscription cancelled immediately, user tier reset")

    # ========== SUBSCRIPTION DELETED ==========       
    elif event['type'] == 'customer.subscription.deleted':
                # SUBSCRIPTION ENDED/DELETED
        subscription = event['data']['object']
        db_sub = await get_subscription_by_stripe_id(db, subscription['id'])
                
        if db_sub:
            await update_subscription(
                db,
                db_sub.id,
                status='cancelled',
                ended_at=datetime.utcnow(),
                cancelled_at=datetime.fromtimestamp(subscription['canceled_at']) if subscription.get('canceled_at') else None
            )

            # ADD THIS: Update user's subscription_tier to NULL when deleted
            from sqlalchemy import text
            await db.execute(
                text("UPDATE stud_hub_schema.users SET subscription_tier = NULL WHERE user_id = (SELECT user_id FROM stud_hub_schema.customers WHERE id = :customer_id)"),
                {"customer_id": str(db_sub.customer_id)}
            )
            await db.commit()
            print("🛑 Subscription ended/deleted, user tier reset")

            # SEND EXPIRY/CANCELLATION EMAIL
            try:
                from sqlalchemy import text as text2
                user_result = await db.execute(
                    text2("""
                        SELECT u.email, u.name 
                        FROM stud_hub_schema.users u
                        JOIN stud_hub_schema.customers c ON c.user_id = u.user_id
                        WHERE c.id = :customer_id
                    """),
                    {"customer_id": str(db_sub.customer_id)}
                )
                user_row = user_result.fetchone()
                if user_row:
                    await send_subscription_expiry_email(
                        to_email=user_row.email,
                        user_name=user_row.name,
                        plan_name="your plan",          # or fetch plan name via db_sub.plan_id
                        expires_at=datetime.utcnow(),
                        days_remaining=0
                    )
                    print(f"📧 Expiry email sent to {user_row.email}")
            except Exception as e:
                print(f"❌ Expiry email failed (non-blocking): {e}")


    # ========== NEW: PRODUCT CREATED ==========
    elif event['type'] == 'product.created':
        product = event['data']['object']
        
        try:
            await create_plan_from_stripe(db, product)
            invalidate_plans_cache()  
            print(f"✅ Plan created from Stripe: {product['name']}")
        except Exception as e:
            print(f"❌ Failed to create plan: {str(e)}")
    
    # ========== NEW: PRODUCT UPDATED ==========
    elif event['type'] == 'product.updated':
        product = event['data']['object']
        
        try:
            await update_plan_from_stripe(db, product)
            invalidate_plans_cache()
            print(f"🔄 Plan updated from Stripe: {product['name']}")
        except Exception as e:
            print(f"❌ Failed to update plan: {str(e)}")
    
    # ========== NEW: PRICE CREATED ==========
    elif event['type'] == 'price.created':
        price = event['data']['object']
        
        try:
            await create_plan_price_from_stripe(db, price)
            invalidate_plans_cache()
            print(f"✅ Price created from Stripe: {price['id']}")
        except Exception as e:
            print(f"❌ Failed to create price: {str(e)}")
    
    # ========== NEW: PRICE UPDATED ==========
    elif event['type'] == 'price.updated':
        price = event['data']['object']
        
        try:
            await update_plan_price_from_stripe(db, price)
            invalidate_plans_cache()
            print(f"🔄 Price updated from Stripe: {price['id']}")
        except Exception as e:
            print(f"❌ Failed to update price: {str(e)}")

    # ========== NEW: PRODUCT DELETED ==========
    elif event['type'] == 'product.deleted':
        product = event['data']['object']
        
        try:
            await delete_plan_from_stripe(db, product['id'])
            invalidate_plans_cache()
            print(f"🗑️ Plan deleted from Stripe: {product['name']}")
        except Exception as e:
            print(f"❌ Failed to delete plan: {str(e)}")
    
    # ========== NEW: PRICE DELETED ==========
    elif event['type'] == 'price.deleted':
        price = event['data']['object']
        
        try:
            await delete_plan_price_from_stripe(db, price['id'])
            invalidate_plans_cache()
            print(f"🗑️ Price deleted from Stripe: {price['id']}")
        except Exception as e:
            print(f"❌ Failed to delete price: {str(e)}")

    return {"status": "ok"}

# ========== PAYMENT METHODS ==========

@app.get("/payment-methods/{user_id}")
async def get_payment_methods(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get user's payment methods from Stripe"""
    try:
        customer = await get_customer(db, user_id)
        if not customer:
            return {
                "payment_methods": [],
                "has_payment_method": False
            }

        payment_methods = StripeClient.get_payment_methods(customer.stripe_customer_id)

        return {
            "payment_methods": payment_methods,
            "has_payment_method": len(payment_methods) > 0
        }
    except Exception as e:
        print(f"❌ Error fetching payment methods: {str(e)}")
        raise HTTPException(500, f"Failed to fetch payment methods: {str(e)}")


# ========== CUSTOMER PORTAL ==========

class CustomerPortalRequest(BaseModel):
    user_id: str


@app.post("/create-customer-portal-session")
async def create_customer_portal_session(
    request: CustomerPortalRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe Customer Portal session"""
    try:
        user_id = UUID(request.user_id)
        print(f"🔍 Creating portal for user: {user_id}")

        customer = await get_customer(db, user_id)
        if not customer:
            print(f"❌ Customer not found for user: {user_id}")
            raise HTTPException(status_code=404, detail="Customer not found. Please subscribe first.")

        print(f" Found customer: {customer.stripe_customer_id}")

        #  Dynamic return URL — no hardcoding
        environment = os.getenv("ENVIRONMENT", "development")
        return_url = (
            "https://app.edhub360.com"
            if environment == "production"
            else "https://edhub360.github.io/StudentHub/"
        )

        portal_url = StripeClient.create_customer_portal_session(
            customer.stripe_customer_id,
            return_url=return_url
        )

        print(f" Portal URL created: {portal_url}")
        return {"url": portal_url}

    except ValueError as e:
        print(f"❌ Invalid user_id format: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        print(f"❌ Error creating portal session: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")


#  DELETE /activate-subscription — free plan now goes through Stripe checkout
#  DELETE /free-plan-status — no longer needed


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



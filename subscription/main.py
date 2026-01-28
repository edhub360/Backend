from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import stripe
from dotenv import load_dotenv
import os
from datetime import datetime
from uuid import UUID
from typing import List

from stripe_client import StripeClient
from crud import *
from schema import *
from db import get_db, engine
from models import Base, User
from auth import get_current_user


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
    # 1. Get/create customer
    customer = await get_customer(db, request.user_id)
    if not customer:
        stripe_cust_id = StripeClient.create_customer(str(request.user_id))
        customer = await create_customer(db, request.user_id, stripe_cust_id)
    
    # 2. Get price
    price = await get_plan_price(db, request.plan_id, request.billing_period)
    if not price:
        raise HTTPException(404, "Plan price not found")
    
    # 3. Create checkout WITH METADATA
    url = StripeClient.create_checkout_session(
        customer.stripe_customer_id,
        price.stripe_price_id,
        "http://localhost:3000/success",
        "http://localhost:3000/cancel",
        {"user_id": str(request.user_id)}  # ADD THIS LINE!
    )
    
    return CheckoutSessionResponse(url=url)


@app.get("/plans", response_model=List[PlanOut])
async def get_plans(db: AsyncSession = Depends(get_db)):
    """Get all available subscription plans."""
    return await get_all_plans(db)


@app.get("/subscriptions/{user_id}", response_model=SubscriptionOut)
async def get_subscription_by_user_id(
    user_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """Get subscription by user ID."""
    sub = await get_user_subscription(db, user_id)
    if not sub:
        raise HTTPException(404, "No active subscription")
    return sub


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
    
    print(f"🔔 Webhook Event: {event['type']}")  # ADD THIS
    
    if event['type'] == 'checkout.session.completed':
        print("✅ CHECKOUT SESSION COMPLETED TRIGGERED!")  # ADD THIS
        
        session = event['data']['object']
        print(f"📦 Session ID: {session.get('id')}")  # ADD THIS
        print(f"💳 Subscription: {session.get('subscription')}")  # ADD THIS
        print(f"👤 Metadata: {session.get('metadata')}")  # ADD THIS
        
        parsed = StripeClient.parse_checkout_session(session)
        print(f"🔍 Parsed: {parsed}")  # ADD THIS - CRITICAL!
        
        if parsed['subscription_id'] and parsed['user_id']:
            print("✅ ENTERING IF BLOCK - Has sub_id + user_id")  # ADD THIS
            
            user_id = UUID(parsed['user_id'])
            stripe_sub = StripeClient.retrieve_subscription(parsed['subscription_id'])
            plan_price_id = stripe_sub['items']['data'][0]['price']['id']
            
            print(f"🔍 Looking for price: {plan_price_id}")
            
            price = await get_plan_price_by_stripe_id(db, plan_price_id)
            print(f"✅ Price found: {price}")
            
            customer = await get_customer(db, user_id)
            print(f"👤 Customer: {customer}")
            
            if price and customer:
                await create_subscription(
                    db, 
                    customer.id,
                    price.plan_id,
                    parsed['subscription_id'],
                    datetime.fromtimestamp(stripe_sub['current_period_start']),
                    datetime.fromtimestamp(stripe_sub['current_period_end'])
                )
                print("🎉 Subscription created!")

            else:
                print(f"❌ FAILED - price: {price}, customer: {customer}")  # ADD THIS
        else:
            print(f"❌ IF CONDITION FAILED - sub_id: {parsed.get('subscription_id')}, user_id: {parsed.get('user_id')}")  # ADD THIS
    
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
                print("❌ Subscription cancelled immediately")
            
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
            print("🛑 Subscription ended/deleted")
             
    return {"status": "ok"}

@app.post("/activate-subscription")
async def activate_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate free trial subscription for first-time users."""
    print(f"\n{'='*60}")
    print(f" DEBUG: ACTIVATE SUBSCRIPTION endpoint called")
    print(f" DEBUG: User: {current_user.email}")
    print(f" DEBUG: Current subscription_tier: {current_user.subscription_tier}")
    print(f"{'='*60}\n")
    
    try:
        # Check if already has subscription
        if current_user.subscription_tier:
            print(f" DEBUG: Subscription already active")
            return {
                "message": "Subscription already active",
                "subscription_tier": current_user.subscription_tier,
                "status": "already_active"
            }
        
        print(f" DEBUG: Setting subscription_tier to 'free'...")
        # Activate free trial
        current_user.subscription_tier = 'free'
        
        print(f" DEBUG: Committing to database...")
        await db.commit()
        await db.refresh(current_user)
        
        print(f" DEBUG: Free trial activated successfully!")
        
        return {
            "message": "Free trial activated successfully",
            "subscription_tier": "free",
            "status": "activated"
        }
        
    except Exception as e:
        print(f" DEBUG: Activation error: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to activate subscription"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



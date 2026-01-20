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
from schemas import *
from database import get_db, engine
from models import Base

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
app = FastAPI(title="Subscription Service (Async)")

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
    
    # 3. Create checkout
    url = StripeClient.create_checkout_session(
        customer.stripe_customer_id,
        price.stripe_price_id,
        "http://localhost:3000/success",
        "http://localhost:3000/cancel"
    )
    
    return CheckoutSessionResponse(url=url)

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
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        parsed = StripeClient.parse_checkout_session(session)
        
        if parsed['subscription_id'] and parsed['user_id']:
            user_id = UUID(parsed['user_id'])
            stripe_sub = StripeClient.retrieve_subscription(parsed['subscription_id'])
            plan_price_id = stripe_sub['items']['data'][0]['price']['id']
            
            price = await get_plan_price_by_stripe_id(db, plan_price_id)
            customer = await get_customer(db, user_id)
            
            if price and customer:
                await create_subscription(
                    db, 
                    customer.id,
                    price.plan_id,
                    parsed['subscription_id'],
                    datetime.fromtimestamp(stripe_sub['current_period_start']),
                    datetime.fromtimestamp(stripe_sub['current_period_end'])
                )
    
    elif event['type'] == 'invoice.payment_succeeded':
        # Handle renewal
        pass
    
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

# ========== PLAN PRICE SCHEMAS ==========
class PlanPriceOut(BaseModel):
    id: UUID
    billing_period: str
    currency: str
    amount: int  # Amount in smallest currency unit (499 = ₹4.99)
    stripe_price_id: str
    is_active: bool
    
    class Config:
        from_attributes = True

# ========== PLAN SCHEMAS ==========
class PlanOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None  # ✅ ADD THIS
    features_json: Dict[str, Any]
    is_active: bool
    prices: List[PlanPriceOut] = []  # Already present
    
    class Config:
        from_attributes = True

# ========== CHECKOUT SCHEMAS ==========
class CheckoutSessionRequest(BaseModel):
    user_id: UUID
    plan_id: UUID
    billing_period: str = Field(..., pattern="^(monthly|yearly)$")

class CheckoutSessionResponse(BaseModel):
    url: str

# ========== SUBSCRIPTION SCHEMAS ==========
class SubscriptionOut(BaseModel):
    id: UUID
    customer_id: UUID
    plan_id: UUID
    status: str
    stripe_subscription_id: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ========== CANCEL SUBSCRIPTION SCHEMA ==========
class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = True

# Add this to your schema.py file
from pydantic import BaseModel

class CustomerPortalRequest(BaseModel):
    user_id: str

class CustomerPortalResponse(BaseModel):
    url: str


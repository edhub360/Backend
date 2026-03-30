from pydantic import BaseModel, Field, computed_field, model_validator
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
    billing_period: str = Field(pattern=r"^(monthly|yearly|7_day)$")  
    success_url: str
    cancel_url: str

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

    # Not a DB column — populated manually or via validator
    plan_name: str = ""

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_plan_name(cls, data: Any) -> Any:
        # If data is an ORM object with a loaded `plan` relationship
        if hasattr(data, "plan") and data.plan is not None:
            # Sets plan_name from relationship before field validation
            data.__dict__["plan_name"] = data.plan.name.lower().strip()
        return data
# ========== CANCEL SUBSCRIPTION SCHEMA ==========
class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = True

# Add this to your schema.py file
from pydantic import BaseModel

class CustomerPortalRequest(BaseModel):
    user_id: str

class CustomerPortalResponse(BaseModel):
    url: str

#redeploy
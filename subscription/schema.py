from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class PlanOut(BaseModel):
    id: UUID
    name: str
    features_json: Dict[str, Any]
    is_active: bool

class CheckoutSessionRequest(BaseModel):
    user_id: UUID
    plan_id: UUID
    billing_period: str = Field(..., pattern="^(monthly|yearly)$")

class CheckoutSessionResponse(BaseModel):
    url: str

class SubscriptionOut(BaseModel):
    id: UUID
    status: str
    current_period_end: datetime
    plan: PlanOut
    cancel_at: Optional[datetime] = None

class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = True

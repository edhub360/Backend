from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db import Base

import uuid

class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = {"schema": "stud_hub_schema"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    features_json = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    prices = relationship("PlanPrice", back_populates="plan", cascade="all, delete-orphan")

class PlanPrice(Base):
    __tablename__ = "plan_prices"
    __table_args__ = {"schema": "stud_hub_schema"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.plans.id"), nullable=False)
    billing_period = Column(String(20), nullable=False)
    currency = Column(String(3), nullable=False)
    amount = Column(Integer, nullable=False)
    stripe_price_id = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    plan = relationship("Plan", back_populates="prices")


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "stud_hub_schema"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.users.user_id"), nullable=False)
    stripe_customer_id = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "stud_hub_schema"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.customers.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.plans.id"), nullable=False)
    status = Column(String(30), nullable=False)
    stripe_subscription_id = Column(String(100), unique=True, nullable=False)
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    trial_ends_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = {"schema": "stud_hub_schema"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.subscriptions.id"), nullable=False)
    stripe_invoice_id = Column(String(100), unique=True, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(20), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"
    __table_args__ = {"schema": "stud_hub_schema"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.invoices.id"), nullable=False)
    stripe_price_id = Column(String(100), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    amount = Column(Integer, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)


class User(Base):
    """User model for subscription updates."""
    __tablename__ = "users"
    __table_args__ = {"schema": "stud_hub_schema"}

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    subscription_tier = Column(String)


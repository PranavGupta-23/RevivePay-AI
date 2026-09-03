"""ORM table definitions for ARSA."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship

from backend.database import Base


def now() -> dt.datetime:
    return dt.datetime.utcnow()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_ref = Column(String, unique=True, index=True)  # e.g. CUST-000123
    ltv_proxy = Column(Float, default=0.0)  # customer lifetime value proxy (INR)
    subscription_status = Column(String, default="NONE")  # NONE / ACTIVE / CHURNED
    consent_flag = Column(Boolean, default=True)  # False = do-not-contact
    recent_activity_score = Column(Float, default=0.5)  # 0..1
    previous_failures_count = Column(Integer, default=0)
    previous_successful_recoveries = Column(Integer, default=0)
    previous_contacts_count = Column(Integer, default=0)

    transactions = relationship("Transaction", back_populates="customer")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    amount = Column(Float, nullable=False)
    payment_method = Column(String, default="card")
    failure_raw_text = Column(String, default="")
    failure_type = Column(String, index=True)  # normalized enum value
    status = Column(String, default="FAILED", index=True)
    # FAILED / RECOVERED / ABSTAINED / ESCALATED / IN_REVIEW

    retry_count = Column(Integer, default=0)
    contact_count = Column(Integer, default=0)
    last_action_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)

    customer = relationship("Customer", back_populates="transactions")


class StrategyMemory(Base):
    __tablename__ = "strategy_memory"

    id = Column(Integer, primary_key=True, index=True)
    failure_type = Column(String, index=True)
    strategy = Column(String, index=True)
    attempts = Column(Integer, default=0)
    successes = Column(Integer, default=0)
    ema_rate = Column(Float, default=0.5)  # exponential moving average success rate
    updated_at = Column(DateTime, default=now, onupdate=now)


class StrategyMemoryHistory(Base):
    """Snapshot row written every time a StrategyMemory entry is updated,
    so the dashboard can plot how EMA success rate evolves over time."""
    __tablename__ = "strategy_memory_history"

    id = Column(Integer, primary_key=True, index=True)
    failure_type = Column(String, index=True)
    strategy = Column(String, index=True)
    attempts = Column(Integer)
    successes = Column(Integer)
    ema_rate = Column(Float)
    recorded_at = Column(DateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    timestamp = Column(DateTime, default=now)
    failure_type = Column(String)
    candidates_json = Column(Text)  # JSON: all candidate strategies + probs + EV
    selected_strategy = Column(String)
    expected_net_recovery = Column(Float)
    guardrail_result = Column(String)  # APPROVED / BLOCKED / REROUTED / ESCALATED
    guardrail_reason = Column(String, default="")
    execution_result = Column(String, default="")  # SUCCESS / FAILURE / N/A ...
    model_version = Column(String)
    policy_version = Column(String)
    human_override = Column(String, default="")
    final_outcome = Column(String, default="")
    idempotency_key = Column(String, unique=True, index=True)


class HumanReview(Base):
    __tablename__ = "human_review"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    reason = Column(String)
    recommended_strategy = Column(String)
    status = Column(String, default="PENDING")  # PENDING / APPROVED / REJECTED
    override_strategy = Column(String, default="")
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)

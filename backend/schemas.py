"""Pydantic schemas for API request/response bodies."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel


class CustomerOut(BaseModel):
    id: int
    customer_ref: str
    ltv_proxy: float
    subscription_status: str
    consent_flag: bool
    recent_activity_score: float
    previous_failures_count: int
    previous_successful_recoveries: int
    previous_contacts_count: int

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: int
    customer_id: int
    amount: float
    payment_method: str
    failure_raw_text: str
    failure_type: str
    status: str
    retry_count: int
    contact_count: int
    created_at: dt.datetime

    class Config:
        from_attributes = True


class NewFailureRequest(BaseModel):
    customer_ref: Optional[str] = None
    amount: float
    payment_method: str = "card"
    failure_raw_text: str


class CandidateStrategy(BaseModel):
    strategy: str
    ml_probability: float
    memory_probability: Optional[float] = None
    memory_attempts: int = 0
    blended_probability: float
    intervention_cost: float
    friction_penalty: float
    expected_net_recovery: float


class DecisionExplanation(BaseModel):
    transaction_id: int
    amount: float
    failure_type: str
    candidates: list[CandidateStrategy]
    recommended_strategy: str
    reason: str


class ExecuteActionResponse(BaseModel):
    transaction_id: int
    selected_strategy: str
    guardrail_result: str
    guardrail_reason: str
    execution_result: str
    final_outcome: str
    amount_recovered: float
    expected_net_recovery: float
    audit_log_id: int


class StrategyMemoryOut(BaseModel):
    failure_type: str
    strategy: str
    attempts: int
    successes: int
    ema_rate: float

    class Config:
        from_attributes = True


class SimulateOutcomesRequest(BaseModel):
    failure_type: str
    strategy: str
    n: int = 100
    override_success_probability: Optional[float] = None
    use_drift_table: bool = True


class HumanReviewDecision(BaseModel):
    action: str  # APPROVE / REJECT / OVERRIDE
    override_strategy: Optional[str] = None


class AuditLogOut(BaseModel):
    id: int
    transaction_id: int
    timestamp: dt.datetime
    failure_type: str
    selected_strategy: str
    expected_net_recovery: float
    guardrail_result: str
    guardrail_reason: str
    execution_result: str
    model_version: str
    policy_version: str
    human_override: str
    final_outcome: str

    class Config:
        from_attributes = True
        protected_namespaces = ()

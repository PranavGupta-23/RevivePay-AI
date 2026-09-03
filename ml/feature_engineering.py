from __future__ import annotations
from typing import Any
import numpy as np

FAILURE_TYPES = [
    "TEMPORARY_NETWORK_FAILURE",
    "INSUFFICIENT_FUNDS",
    "INVALID_PAYMENT_METHOD",
    "CHECKOUT_ABANDONED",
    "REPEATED_FAILURE",
    "UNKNOWN",
]

STRATEGIES = [
    "RETRY_NOW",
    "RETRY_LATER",
    "SEND_PAYMENT_LINK",
    "SEND_RECOVERY_MESSAGE",
    "REQUEST_PAYMENT_METHOD_UPDATE",
    "ESCALATE_TO_HUMAN",
    "ABSTAIN",
]

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet"]

NUMERIC_FEATURES = [
    "amount_log",
    "previous_failures_count",
    "previous_successful_recoveries",
    "previous_contacts_count",
    "ltv_proxy_log",
    "recent_activity_score",
    "retry_count",
]
CATEGORICAL_FEATURES = [
    "failure_type",
    "strategy",
    "payment_method",
    "subscription_status",
]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_feature_row(
    *,
    amount: float,
    failure_type: str,
    strategy: str,
    payment_method: str,
    subscription_status: str,
    previous_failures_count: int,
    previous_successful_recoveries: int,
    previous_contacts_count: int,
    ltv_proxy: float,
    recent_activity_score: float,
    retry_count: int,
) -> dict[str, Any]:
    """Build a single feature dict for one (transaction, candidate strategy) pair."""
    return {
        "amount_log": float(np.log1p(max(amount, 0.0))),
        "previous_failures_count": int(previous_failures_count),
        "previous_successful_recoveries": int(previous_successful_recoveries),
        "previous_contacts_count": int(previous_contacts_count),
        "ltv_proxy_log": float(np.log1p(max(ltv_proxy, 0.0))),
        "recent_activity_score": float(recent_activity_score),
        "retry_count": int(retry_count),
        "failure_type": failure_type,
        "strategy": strategy,
        "payment_method": payment_method,
        "subscription_status": subscription_status,
    }

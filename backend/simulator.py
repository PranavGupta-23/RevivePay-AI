"""
Local, seeded payment recovery simulator.

No real payment gateway is ever contacted. Given the selected strategy and
the transaction's context, this module samples a plausible outcome. The
"true" probability table intentionally matches (roughly) the generative
model used for the synthetic training data, so that a well-trained model +
adaptive memory should converge toward good decisions -- while still
allowing controlled "drift" (see config.DRIFTED_SUCCESS_PROBABILITIES) for
the live adaptation demo.
"""
from __future__ import annotations

import numpy as np

from backend.config import RANDOM_SEED

_BASE_TRUE_PROB = {
    ("TEMPORARY_NETWORK_FAILURE", "RETRY_NOW"): 0.31,
    ("TEMPORARY_NETWORK_FAILURE", "RETRY_LATER"): 0.72,
    ("TEMPORARY_NETWORK_FAILURE", "SEND_PAYMENT_LINK"): 0.42,
    ("TEMPORARY_NETWORK_FAILURE", "SEND_RECOVERY_MESSAGE"): 0.38,
    ("INSUFFICIENT_FUNDS", "RETRY_NOW"): 0.10,
    ("INSUFFICIENT_FUNDS", "RETRY_LATER"): 0.55,
    ("INSUFFICIENT_FUNDS", "SEND_RECOVERY_MESSAGE"): 0.33,
    ("INSUFFICIENT_FUNDS", "SEND_PAYMENT_LINK"): 0.30,
    ("INVALID_PAYMENT_METHOD", "REQUEST_PAYMENT_METHOD_UPDATE"): 0.74,
    ("INVALID_PAYMENT_METHOD", "SEND_PAYMENT_LINK"): 0.28,
    ("INVALID_PAYMENT_METHOD", "SEND_RECOVERY_MESSAGE"): 0.15,
    ("CHECKOUT_ABANDONED", "SEND_PAYMENT_LINK"): 0.48,
    ("CHECKOUT_ABANDONED", "SEND_RECOVERY_MESSAGE"): 0.34,
    ("CHECKOUT_ABANDONED", "RETRY_LATER"): 0.18,
    ("REPEATED_FAILURE", "ESCALATE_TO_HUMAN"): 0.40,
    ("REPEATED_FAILURE", "REQUEST_PAYMENT_METHOD_UPDATE"): 0.22,
    ("UNKNOWN", "SEND_RECOVERY_MESSAGE"): 0.20,
    ("UNKNOWN", "ESCALATE_TO_HUMAN"): 0.25,
}

_rng = np.random.default_rng(RANDOM_SEED + 999)


def simulate_action(failure_type: str, strategy: str) -> tuple[str, bool]:
    """
    Executes the (simulated) recovery action.
    Returns (execution_result, success) where execution_result is a short
    human-readable status string and success is a bool used to update
    strategy memory / transaction status.
    """
    if strategy == "ABSTAIN":
        return "NO_ACTION_TAKEN", False
    if strategy == "ESCALATE_TO_HUMAN":
        return "PENDING_HUMAN_REVIEW", False

    prob = _BASE_TRUE_PROB.get((failure_type, strategy), 0.15)
    success = bool(_rng.random() < prob)
    if success:
        return "SUCCESS", True

    # Occasionally a failed attempt still shows a "delayed" signal, useful
    # for realism in the audit log even though we treat it as a failure now.
    delayed = _rng.random() < 0.10
    return ("DELAYED_NO_RESULT_YET" if delayed else "FAILURE"), False


def simulate_bulk_outcomes(success_probability: float, n: int) -> list[bool]:
    """Used by the '/memory/simulate' endpoint to bulk-feed strategy memory
    with n Bernoulli(success_probability) outcomes."""
    draws = _rng.random(n) < success_probability
    return [bool(x) for x in draws]

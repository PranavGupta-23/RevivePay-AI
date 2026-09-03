from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import RANDOM_SEED, RAW_DATA_PATH  # noqa: E402
from ml.feature_engineering import (  # noqa: E402
    FAILURE_TYPES, STRATEGIES, PAYMENT_METHODS, build_feature_row,
)

N_TRANSACTIONS = 12000

BASE_SUCCESS_PROB = {
    ("TEMPORARY_NETWORK_FAILURE", "RETRY_NOW"): 0.31,
    ("TEMPORARY_NETWORK_FAILURE", "RETRY_LATER"): 0.72,
    ("TEMPORARY_NETWORK_FAILURE", "SEND_PAYMENT_LINK"): 0.42,
    ("TEMPORARY_NETWORK_FAILURE", "SEND_RECOVERY_MESSAGE"): 0.38,
    ("TEMPORARY_NETWORK_FAILURE", "ABSTAIN"): 0.02,

    ("INSUFFICIENT_FUNDS", "RETRY_NOW"): 0.10,
    ("INSUFFICIENT_FUNDS", "RETRY_LATER"): 0.55,
    ("INSUFFICIENT_FUNDS", "SEND_RECOVERY_MESSAGE"): 0.33,
    ("INSUFFICIENT_FUNDS", "SEND_PAYMENT_LINK"): 0.30,
    ("INSUFFICIENT_FUNDS", "ABSTAIN"): 0.02,

    ("INVALID_PAYMENT_METHOD", "RETRY_NOW"): 0.03,
    ("INVALID_PAYMENT_METHOD", "RETRY_LATER"): 0.05,
    ("INVALID_PAYMENT_METHOD", "REQUEST_PAYMENT_METHOD_UPDATE"): 0.74,
    ("INVALID_PAYMENT_METHOD", "SEND_PAYMENT_LINK"): 0.28,
    ("INVALID_PAYMENT_METHOD", "SEND_RECOVERY_MESSAGE"): 0.15,
    ("INVALID_PAYMENT_METHOD", "ABSTAIN"): 0.02,

    ("CHECKOUT_ABANDONED", "SEND_PAYMENT_LINK"): 0.48,
    ("CHECKOUT_ABANDONED", "SEND_RECOVERY_MESSAGE"): 0.34,
    ("CHECKOUT_ABANDONED", "RETRY_LATER"): 0.18,
    ("CHECKOUT_ABANDONED", "ABSTAIN"): 0.03,

    ("REPEATED_FAILURE", "ESCALATE_TO_HUMAN"): 0.40,
    ("REPEATED_FAILURE", "REQUEST_PAYMENT_METHOD_UPDATE"): 0.22,
    ("REPEATED_FAILURE", "ABSTAIN"): 0.05,
    ("REPEATED_FAILURE", "RETRY_NOW"): 0.04,
    ("REPEATED_FAILURE", "RETRY_LATER"): 0.08,

    ("UNKNOWN", "SEND_RECOVERY_MESSAGE"): 0.20,
    ("UNKNOWN", "ESCALATE_TO_HUMAN"): 0.25,
    ("UNKNOWN", "ABSTAIN"): 0.05,
}

POLICY_STRATEGY_WEIGHTS = {
    "TEMPORARY_NETWORK_FAILURE": {
        "RETRY_NOW": 0.30, "RETRY_LATER": 0.40, "SEND_PAYMENT_LINK": 0.15,
        "SEND_RECOVERY_MESSAGE": 0.10, "ABSTAIN": 0.05,
    },
    "INSUFFICIENT_FUNDS": {
        "RETRY_NOW": 0.25, "RETRY_LATER": 0.40, "SEND_RECOVERY_MESSAGE": 0.20,
        "SEND_PAYMENT_LINK": 0.10, "ABSTAIN": 0.05,
    },
    "INVALID_PAYMENT_METHOD": {
        "REQUEST_PAYMENT_METHOD_UPDATE": 0.45, "SEND_PAYMENT_LINK": 0.20,
        "SEND_RECOVERY_MESSAGE": 0.15, "RETRY_NOW": 0.10, "RETRY_LATER": 0.05,
        "ABSTAIN": 0.05,
    },
    "CHECKOUT_ABANDONED": {
        "SEND_PAYMENT_LINK": 0.45, "SEND_RECOVERY_MESSAGE": 0.35,
        "RETRY_LATER": 0.15, "ABSTAIN": 0.05,
    },
    "REPEATED_FAILURE": {
        "ESCALATE_TO_HUMAN": 0.35, "REQUEST_PAYMENT_METHOD_UPDATE": 0.20,
        "RETRY_NOW": 0.15, "RETRY_LATER": 0.15, "ABSTAIN": 0.15,
    },
    "UNKNOWN": {
        "SEND_RECOVERY_MESSAGE": 0.45, "ESCALATE_TO_HUMAN": 0.30, "ABSTAIN": 0.25,
    },
}

FAILURE_TYPE_WEIGHTS = {
    "TEMPORARY_NETWORK_FAILURE": 0.28,
    "INSUFFICIENT_FUNDS": 0.24,
    "INVALID_PAYMENT_METHOD": 0.20,
    "CHECKOUT_ABANDONED": 0.16,
    "REPEATED_FAILURE": 0.08,
    "UNKNOWN": 0.04,
}


def sample_customer(rng: np.random.Generator) -> dict:
    previous_failures = int(rng.poisson(1.2))
    previous_contacts = int(min(rng.poisson(1.0), 10))
    previous_successes = int(rng.binomial(max(previous_failures, 0), 0.45))
    return {
        "ltv_proxy": float(max(rng.normal(15000, 12000), 0)),
        "subscription_status": rng.choice(
            ["NONE", "ACTIVE", "CHURNED"], p=[0.5, 0.4, 0.1]
        ),
        "consent_flag": bool(rng.random() > 0.05),
        "recent_activity_score": float(np.clip(rng.normal(0.5, 0.2), 0, 1)),
        "previous_failures_count": previous_failures,
        "previous_successful_recoveries": previous_successes,
        "previous_contacts_count": previous_contacts,
    }


def true_success_probability(
    failure_type: str,
    strategy: str,
    previous_contacts_count: int,
    previous_failures_count: int,
    recent_activity_score: float,
    subscription_status: str,
    rng: np.random.Generator,
) -> float:
    base = BASE_SUCCESS_PROB.get((failure_type, strategy), 0.05)

    # Excessive prior contacts reduce recovery probability (fatigue effect).
    contact_penalty = 0.04 * max(previous_contacts_count - 1, 0)

    # Repeated prior failures reduce recovery probability slightly further
    # (beyond the REPEATED_FAILURE category itself).
    failure_penalty = 0.02 * max(previous_failures_count - 2, 0)

    # More engaged / active customers recover slightly better.
    activity_bonus = 0.10 * (recent_activity_score - 0.5)

    # Active subscribers are a bit more likely to fix payment issues.
    sub_bonus = 0.05 if subscription_status == "ACTIVE" else 0.0

    prob = base - contact_penalty - failure_penalty + activity_bonus + sub_bonus
    prob += rng.normal(0, 0.03)  # small observation noise
    return float(np.clip(prob, 0.01, 0.97))


def generate(n: int = N_TRANSACTIONS, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []

    failure_types = list(FAILURE_TYPE_WEIGHTS.keys())
    failure_probs = list(FAILURE_TYPE_WEIGHTS.values())

    for i in range(n):
        failure_type = rng.choice(failure_types, p=failure_probs)
        customer = sample_customer(rng)

        weights = POLICY_STRATEGY_WEIGHTS[failure_type]
        strategy = rng.choice(list(weights.keys()), p=list(weights.values()))

        amount = float(max(rng.lognormal(mean=8.6, sigma=0.9), 100))
        payment_method = rng.choice(PAYMENT_METHODS, p=[0.5, 0.3, 0.15, 0.05])
        retry_count = int(min(rng.poisson(0.6), 4))

        prob = true_success_probability(
            failure_type=failure_type,
            strategy=strategy,
            previous_contacts_count=customer["previous_contacts_count"],
            previous_failures_count=customer["previous_failures_count"],
            recent_activity_score=customer["recent_activity_score"],
            subscription_status=customer["subscription_status"],
            rng=rng,
        )
        outcome = int(rng.random() < prob)

        feature_row = build_feature_row(
            amount=amount,
            failure_type=failure_type,
            strategy=strategy,
            payment_method=payment_method,
            subscription_status=customer["subscription_status"],
            previous_failures_count=customer["previous_failures_count"],
            previous_successful_recoveries=customer["previous_successful_recoveries"],
            previous_contacts_count=customer["previous_contacts_count"],
            ltv_proxy=customer["ltv_proxy"],
            recent_activity_score=customer["recent_activity_score"],
            retry_count=retry_count,
        )
        feature_row["amount"] = amount
        feature_row["outcome"] = outcome
        feature_row["true_probability"] = prob
        feature_row["transaction_index"] = i
        rows.append(feature_row)

    df = pd.DataFrame(rows)
    return df


def main() -> None:
    df = generate()
    RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"Generated {len(df)} synthetic historical recovery attempts.")
    print(f"Saved to: {RAW_DATA_PATH}")
    print("\nOutcome rate by failure_type / strategy (sanity check):")
    summary = (
        df.groupby(["failure_type", "strategy"])["outcome"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "success_rate", "count": "n"})
        .sort_values(["failure_type", "success_rate"], ascending=[True, False])
    )
    print(summary.round(3))


if __name__ == "__main__":
    main()

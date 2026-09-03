"""Loads the trained sklearn pipeline once and exposes a simple predict API."""
from __future__ import annotations

import json
from functools import lru_cache

import joblib
import pandas as pd

from backend.config import MODEL_PATH, MODEL_METADATA_PATH
from ml.feature_engineering import ALL_FEATURES, build_feature_row


class RecoveryModel:
    def __init__(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Trained model not found at {MODEL_PATH}. "
                "Run `python ml/train_model.py` first."
            )
        self.pipeline = joblib.load(MODEL_PATH)
        with open(MODEL_METADATA_PATH) as f:
            self.metadata = json.load(f)
        self.model_version = self.metadata.get("model_version", "unknown")

    def predict_for_strategies(
        self,
        *,
        amount: float,
        failure_type: str,
        payment_method: str,
        subscription_status: str,
        previous_failures_count: int,
        previous_successful_recoveries: int,
        previous_contacts_count: int,
        ltv_proxy: float,
        recent_activity_score: float,
        retry_count: int,
        candidate_strategies: list[str],
    ) -> dict[str, float]:
        """Return {strategy: P(success)} for every candidate strategy."""
        rows = []
        for strategy in candidate_strategies:
            rows.append(
                build_feature_row(
                    amount=amount,
                    failure_type=failure_type,
                    strategy=strategy,
                    payment_method=payment_method,
                    subscription_status=subscription_status,
                    previous_failures_count=previous_failures_count,
                    previous_successful_recoveries=previous_successful_recoveries,
                    previous_contacts_count=previous_contacts_count,
                    ltv_proxy=ltv_proxy,
                    recent_activity_score=recent_activity_score,
                    retry_count=retry_count,
                )
            )
        df = pd.DataFrame(rows)[ALL_FEATURES]
        probs = self.pipeline.predict_proba(df)[:, 1]
        return {s: float(p) for s, p in zip(candidate_strategies, probs)}


@lru_cache(maxsize=1)
def get_model() -> RecoveryModel:
    return RecoveryModel()

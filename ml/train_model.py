from __future__ import annotations
import json
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import (  # noqa: E402
    RANDOM_SEED, RAW_DATA_PATH, TRAIN_PATH, VAL_PATH, TEST_PATH,
    MODEL_PATH, MODEL_METADATA_PATH, MODEL_VERSION,
)
from ml.feature_engineering import NUMERIC_FEATURES, CATEGORICAL_FEATURES, ALL_FEATURES  # noqa: E402


def load_and_split() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Synthetic data not found at {RAW_DATA_PATH}. "
            "Run `python ml/generate_synthetic_data.py` first."
        )
    df = pd.read_csv(RAW_DATA_PATH)

    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=RANDOM_SEED, stratify=df["outcome"]
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=RANDOM_SEED, stratify=temp_df["outcome"]
    )

    TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(TRAIN_PATH, index=False)
    val_df.to_csv(VAL_PATH, index=False)
    test_df.to_csv(TEST_PATH, index=False)
    return train_df, val_df, test_df


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    model = LogisticRegression(max_iter=1000, C=1.0, random_state=RANDOM_SEED)
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def evaluate(pipeline: Pipeline, df: pd.DataFrame, split_name: str) -> dict:
    X = df[ALL_FEATURES]
    y = df["outcome"]
    proba = pipeline.predict_proba(X)[:, 1]
    metrics = {
        "split": split_name,
        "n": int(len(df)),
        "roc_auc": float(roc_auc_score(y, proba)),
        "brier_score": float(brier_score_loss(y, proba)),
        "log_loss": float(log_loss(y, proba)),
        "base_rate": float(y.mean()),
    }
    return metrics


def main() -> None:
    train_df, val_df, test_df = load_and_split()
    print(f"Train: {len(train_df)}  Val: {len(val_df)}  Test: {len(test_df)}")

    pipeline = build_pipeline()
    pipeline.fit(train_df[ALL_FEATURES], train_df["outcome"])

    val_metrics = evaluate(pipeline, val_df, "validation")
    print("\nValidation metrics:", json.dumps(val_metrics, indent=2))

    # Only evaluated once, at the very end, on data untouched during
    # development/tuning.
    test_metrics = evaluate(pipeline, test_df, "test")
    print("\nHeld-out TEST metrics (report these, do not tune on them):")
    print(json.dumps(test_metrics, indent=2))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    metadata = {
        "model_version": MODEL_VERSION,
        "features": ALL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "random_seed": RANDOM_SEED,
    }
    with open(MODEL_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved metadata to {MODEL_METADATA_PATH}")

if __name__ == "__main__":
    main()

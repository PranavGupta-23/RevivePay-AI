from __future__ import annotations

from backend.llm_client import classify_failure_text


def normalize_failure(raw_text: str) -> str:
    """Returns one of ml.feature_engineering.FAILURE_TYPES."""
    if not raw_text or not raw_text.strip():
        return "UNKNOWN"
    return classify_failure_text(raw_text)

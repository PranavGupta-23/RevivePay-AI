from __future__ import annotations
from backend.config import CANDIDATE_STRATEGIES_BY_FAILURE

_FIXED_STRATEGY = "SEND_RECOVERY_MESSAGE"

def do_nothing(failure_type: str) -> str:
    return "ABSTAIN"

def always_retry_immediately(failure_type: str) -> str:
    candidates = CANDIDATE_STRATEGIES_BY_FAILURE.get(failure_type, [])
    return "RETRY_NOW" if "RETRY_NOW" in candidates else candidates[0]

def fixed_strategy(failure_type: str) -> str:
    candidates = CANDIDATE_STRATEGIES_BY_FAILURE.get(failure_type, [])
    return _FIXED_STRATEGY if _FIXED_STRATEGY in candidates else candidates[0]

def highest_historical_average(failure_type: str, strategy_memory_rows: list[dict]) -> str:
    candidates = CANDIDATE_STRATEGIES_BY_FAILURE.get(failure_type, [])
    relevant = [r for r in strategy_memory_rows if r["failure_type"] == failure_type and r["strategy"] in candidates]
    if not relevant:
        return candidates[0]
    best = max(relevant, key=lambda r: r["ema_rate"])
    return best["strategy"]


BASELINES = {
    "Do Nothing": do_nothing,
    "Always Retry Immediately": always_retry_immediately,
    "Fixed Strategy (Recovery Message)": fixed_strategy,
}

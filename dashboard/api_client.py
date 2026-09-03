from __future__ import annotations
import os
import requests

BACKEND_URL = os.getenv("RevivePay AI_BACKEND_URL", "http://localhost:8000")
TIMEOUT = 15

def _get(path: str, params: dict | None = None):
    r = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def _post(path: str, json: dict | None = None):
    r = requests.post(f"{BACKEND_URL}{path}", json=json or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def is_backend_up() -> bool:
    try:
        requests.get(f"{BACKEND_URL}/health", timeout=3)
        return True
    except Exception:
        return False

def list_transactions(status: str | None = None, limit: int = 200):
    params = {"limit": limit}
    if status:
        params["status"] = status
    return _get("/transactions", params)


def get_transaction(transaction_id: int):
    return _get(f"/transactions/{transaction_id}")


def create_failure(amount: float, payment_method: str, failure_raw_text: str, customer_ref: str | None = None):
    payload = {
        "amount": amount,
        "payment_method": payment_method,
        "failure_raw_text": failure_raw_text,
    }
    if customer_ref:
        payload["customer_ref"] = customer_ref
    return _post("/transactions", payload)

def get_decision(transaction_id: int):
    return _get(f"/decisions/{transaction_id}")

def execute_action(transaction_id: int):
    return _post(f"/actions/execute/{transaction_id}")

def list_memory():
    return _get("/memory")

def memory_history(failure_type: str | None = None, strategy: str | None = None):
    params = {}
    if failure_type:
        params["failure_type"] = failure_type
    if strategy:
        params["strategy"] = strategy
    return _get("/memory/history", params)


def simulate_outcomes(failure_type: str, strategy: str, n: int = 100, use_drift_table: bool = True,
                       override_success_probability: float | None = None):
    payload = {
        "failure_type": failure_type,
        "strategy": strategy,
        "n": n,
        "use_drift_table": use_drift_table,
    }
    if override_success_probability is not None:
        payload["override_success_probability"] = override_success_probability
    return _post("/memory/simulate", payload)

def review_queue():
    return _get("/review/queue")

def decide_review(review_id: int, action: str, override_strategy: str | None = None):
    payload = {"action": action}
    if override_strategy:
        payload["override_strategy"] = override_strategy
    return _post(f"/review/{review_id}/decide", payload)

def list_audit(limit: int = 200):
    return _get("/audit", {"limit": limit})

def get_audit_entry(audit_id: int):
    return _get(f"/audit/{audit_id}")

def overview_metrics():
    return _get("/metrics/overview")

def strategy_performance():
    return _get("/metrics/strategy_performance")

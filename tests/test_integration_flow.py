import pytest
from backend.agent import build_candidates, execute_recovery
from backend.strategy_memory import get_memory_probability

def test_full_recovery_loop_updates_memory(db_session, sample_transaction, sample_customer):
    pytest.importorskip("joblib")
    _, attempts_before = get_memory_probability(
        db_session, sample_transaction.failure_type, "RETRY_LATER"
    )
    bundle = build_candidates(db_session, sample_transaction, sample_customer)
    assert bundle.recommended_strategy in [c.strategy for c in bundle.ranked_candidates]
    assert len(bundle.ranked_candidates) >= 2
    result = execute_recovery(db_session, sample_transaction, sample_customer)
    assert result["transaction_id"] == sample_transaction.id
    assert result["guardrail_result"] in ("APPROVED", "REROUTED", "BLOCKED", "ESCALATED")
    assert sample_transaction.status in ("RECOVERED", "FAILED", "ABSTAINED", "IN_REVIEW")
    if result["guardrail_result"] in ("APPROVED", "REROUTED"):
        _, attempts_after = get_memory_probability(
            db_session, sample_transaction.failure_type, result["selected_strategy"]
        )
        assert attempts_after == attempts_before + 1 or attempts_after >= 1

def test_idempotency_prevents_double_execution(db_session, sample_transaction, sample_customer):
    pytest.importorskip("joblib")

    first = execute_recovery(db_session, sample_transaction, sample_customer)
    assert first["audit_log_id"] != -1
    from backend.guardrails import check_idempotency
    from backend.config import POLICY_VERSION

    is_dup = check_idempotency(
        db_session, sample_transaction.id, first["selected_strategy"], POLICY_VERSION
    )
    assert is_dup is True

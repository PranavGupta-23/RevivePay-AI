from backend.decision_engine import score_candidate, rank_candidates
from backend.guardrails import evaluate_guardrails, make_idempotency_key, check_idempotency
from backend.models_db import AuditLog

def _candidates():
    return rank_candidates(
        [
            score_candidate("RETRY_NOW", 15000, 0.30, 0.30, 0, 0.30),
            score_candidate("RETRY_LATER", 15000, 0.72, 0.72, 0, 0.72),
            score_candidate("SEND_PAYMENT_LINK", 15000, 0.42, 0.42, 0, 0.42),
            score_candidate("ABSTAIN", 15000, 0.02, 0.02, 0, 0.02),
        ]
    )

def test_top_candidate_approved_when_clean(db_session, sample_transaction):
    verdict = evaluate_guardrails(
        db_session, sample_transaction, _candidates(), consent_flag=True, policy_version="v1"
    )
    assert verdict.result == "APPROVED"
    assert verdict.final_strategy == "RETRY_LATER"

def test_max_retry_attempts_blocks_retry_strategies(db_session, sample_transaction):
    sample_transaction.retry_count = 5  # exceeds MAX_RETRY_ATTEMPTS
    candidates = rank_candidates(
        [
            score_candidate("RETRY_LATER", 15000, 0.72, 0.72, 0, 0.72),
            score_candidate("SEND_PAYMENT_LINK", 15000, 0.42, 0.42, 0, 0.42),
            score_candidate("ABSTAIN", 15000, 0.02, 0.02, 0, 0.02),
        ]
    )
    verdict = evaluate_guardrails(
        db_session, sample_transaction, candidates, consent_flag=True, policy_version="v1"
    )
    assert verdict.final_strategy != "RETRY_LATER"
    assert verdict.final_strategy == "SEND_PAYMENT_LINK"
    assert verdict.result == "REROUTED"

def test_no_consent_blocks_contact_strategies(db_session, sample_transaction):
    candidates = rank_candidates(
        [
            score_candidate("SEND_PAYMENT_LINK", 15000, 0.72, 0.72, 0, 0.72),
            score_candidate("RETRY_NOW", 15000, 0.30, 0.30, 0, 0.30),
            score_candidate("ABSTAIN", 15000, 0.02, 0.02, 0, 0.02),
        ]
    )
    verdict = evaluate_guardrails(
        db_session, sample_transaction, candidates, consent_flag=False, policy_version="v1"
    )
    assert verdict.final_strategy == "RETRY_NOW"


def test_negative_expected_value_forces_abstain(db_session, sample_transaction):
    candidates = rank_candidates(
        [
            score_candidate("SEND_PAYMENT_LINK", 10, 0.50, 0.50, 0, 0.50),
        ]
    )
    verdict = evaluate_guardrails(
        db_session, sample_transaction, candidates, consent_flag=True, policy_version="v1"
    )
    assert verdict.final_strategy == "ABSTAIN"
    assert verdict.result == "BLOCKED"


def test_low_confidence_escalates_to_human(db_session, sample_transaction):
    candidates = rank_candidates(
        [
            score_candidate("SEND_PAYMENT_LINK", 15000, 0.10, 0.10, 0, 0.10),
        ]
    )
    verdict = evaluate_guardrails(
        db_session, sample_transaction, candidates, consent_flag=True, policy_version="v1"
    )
    assert verdict.result == "ESCALATED"
    assert verdict.final_strategy == "ESCALATE_TO_HUMAN"

def test_invalid_payment_method_blocks_repeated_blind_retry(db_session, sample_transaction):
    sample_transaction.failure_type = "INVALID_PAYMENT_METHOD"
    sample_transaction.retry_count = 1
    candidates = rank_candidates(
        [
            score_candidate("RETRY_NOW", 15000, 0.60, 0.60, 0, 0.60),
            score_candidate("REQUEST_PAYMENT_METHOD_UPDATE", 15000, 0.50, 0.50, 0, 0.50),
        ]
    )
    verdict = evaluate_guardrails(
        db_session, sample_transaction, candidates, consent_flag=True, policy_version="v1"
    )
    assert verdict.final_strategy == "REQUEST_PAYMENT_METHOD_UPDATE"

def test_idempotency_detects_duplicate(db_session, sample_transaction):
    key = make_idempotency_key(sample_transaction.id, "RETRY_LATER", "v1")
    assert check_idempotency(db_session, sample_transaction.id, "RETRY_LATER", "v1") is False

    db_session.add(
        AuditLog(
            transaction_id=sample_transaction.id,
            failure_type="TEMPORARY_NETWORK_FAILURE",
            candidates_json="[]",
            selected_strategy="RETRY_LATER",
            expected_net_recovery=1000.0,
            guardrail_result="APPROVED",
            guardrail_reason="ok",
            execution_result="SUCCESS",
            model_version="v1",
            policy_version="v1",
            idempotency_key=key,
        )
    )
    db_session.commit()

    assert check_idempotency(db_session, sample_transaction.id, "RETRY_LATER", "v1") is True
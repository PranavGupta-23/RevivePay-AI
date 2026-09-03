from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.orm import Session
from backend.config import (
    CANDIDATE_STRATEGIES_BY_FAILURE, POLICY_VERSION, HIGH_VALUE_THRESHOLD,
    HIGH_RISK_REPEATED_FAILURES,
)
from backend.decision_engine import score_candidate, rank_candidates, explain_choice, CandidateResult
from backend.guardrails import evaluate_guardrails, check_idempotency, make_idempotency_key
from backend.ml_model import get_model
from backend.models_db import Transaction, Customer, HumanReview
from backend.simulator import simulate_action
from backend.strategy_memory import get_memory_probability, blended_probability, update_memory
from backend.audit_logger import log_decision


@dataclass
class DecisionBundle:
    ranked_candidates: list[CandidateResult]
    recommended_strategy: str
    reason: str


def build_candidates(db: Session, transaction: Transaction, customer: Customer) -> DecisionBundle:
    """DECIDE step: score every plausible strategy for this failure type."""
    model = get_model()
    candidate_strategies = CANDIDATE_STRATEGIES_BY_FAILURE.get(
        transaction.failure_type, CANDIDATE_STRATEGIES_BY_FAILURE["UNKNOWN"]
    )

    ml_probs = model.predict_for_strategies(
        amount=transaction.amount,
        failure_type=transaction.failure_type,
        payment_method=transaction.payment_method,
        subscription_status=customer.subscription_status,
        previous_failures_count=customer.previous_failures_count,
        previous_successful_recoveries=customer.previous_successful_recoveries,
        previous_contacts_count=customer.previous_contacts_count,
        ltv_proxy=customer.ltv_proxy,
        recent_activity_score=customer.recent_activity_score,
        retry_count=transaction.retry_count,
        candidate_strategies=candidate_strategies,
    )

    candidates: list[CandidateResult] = []
    for strategy in candidate_strategies:
        ml_prob = ml_probs[strategy]
        memory_rate, attempts = get_memory_probability(db, transaction.failure_type, strategy)
        blended = blended_probability(ml_prob, memory_rate, attempts)
        candidates.append(
            score_candidate(
                strategy=strategy,
                amount=transaction.amount,
                ml_probability=ml_prob,
                memory_probability=memory_rate,
                memory_attempts=attempts,
                blended_probability=blended,
            )
        )

    ranked = rank_candidates(candidates)
    runner_up = ranked[1] if len(ranked) > 1 else None
    reason = explain_choice(ranked[0], runner_up)
    return DecisionBundle(
        ranked_candidates=ranked, recommended_strategy=ranked[0].strategy, reason=reason
    )


def execute_recovery(db: Session, transaction: Transaction, customer: Customer) -> dict:
    """
    Runs the full ACT -> MEASURE -> LEARN loop for one transaction:
      1. DECIDE (build_candidates)
      2. Guardrail gate
      3. Idempotency check
      4. Simulated execution
      5. Strategy memory update (LEARN/ADAPT)
      6. Audit log write
    Returns a plain dict summarizing what happened (used by the API layer).
    """
    bundle = build_candidates(db, transaction, customer)

    idem_key = make_idempotency_key(transaction.id, bundle.recommended_strategy, POLICY_VERSION)
    if check_idempotency(db, transaction.id, bundle.recommended_strategy, POLICY_VERSION):
        return {
            "transaction_id": transaction.id,
            "selected_strategy": bundle.recommended_strategy,
            "guardrail_result": "BLOCKED",
            "guardrail_reason": "Duplicate decision detected (idempotency protection).",
            "execution_result": "SKIPPED_DUPLICATE",
            "final_outcome": "N/A",
            "amount_recovered": 0.0,
            "expected_net_recovery": 0.0,
            "audit_log_id": -1,
        }

    verdict = evaluate_guardrails(
        db=db,
        transaction=transaction,
        ranked_candidates=bundle.ranked_candidates,
        consent_flag=customer.consent_flag,
        policy_version=POLICY_VERSION,
    )

    final_strategy = verdict.final_strategy
    winning_candidate = next(
        (c for c in bundle.ranked_candidates if c.strategy == final_strategy), None
    )
    expected_net_recovery = winning_candidate.expected_net_recovery if winning_candidate else 0.0

    execution_result = "N/A"
    final_outcome = "N/A"
    amount_recovered = 0.0
    success = False

    if verdict.result == "ESCALATED":
        review = HumanReview(
            transaction_id=transaction.id,
            reason=verdict.reason,
            recommended_strategy=bundle.recommended_strategy,
            status="PENDING",
        )
        db.add(review)
        transaction.status = "IN_REVIEW"
        execution_result = "ESCALATED_TO_HUMAN_REVIEW"
        final_outcome = "PENDING_HUMAN_DECISION"

    elif verdict.result == "BLOCKED":
        transaction.status = "ABSTAINED"
        execution_result = "NO_ACTION_TAKEN"
        final_outcome = "ABSTAINED"

    else:  # APPROVED or REROUTED
        execution_result, success = simulate_action(transaction.failure_type, final_strategy)

        if final_strategy in ("RETRY_NOW", "RETRY_LATER"):
            transaction.retry_count += 1
        if final_strategy in ("SEND_PAYMENT_LINK", "SEND_RECOVERY_MESSAGE", "REQUEST_PAYMENT_METHOD_UPDATE"):
            transaction.contact_count += 1
            customer.previous_contacts_count += 1

        # LEARN: update strategy memory with this real observed outcome.
        update_memory(db, transaction.failure_type, final_strategy, success)

        if success:
            transaction.status = "RECOVERED"
            amount_recovered = transaction.amount
            customer.previous_successful_recoveries += 1
            final_outcome = "RECOVERED"
        else:
            transaction.status = "FAILED"
            final_outcome = "STILL_FAILED"

        import datetime as _dt
        transaction.last_action_at = _dt.datetime.utcnow()

    db.add(transaction)
    db.add(customer)
    db.commit()

    audit_row = log_decision(
        db,
        transaction_id=transaction.id,
        failure_type=transaction.failure_type,
        candidates=bundle.ranked_candidates,
        selected_strategy=final_strategy,
        expected_net_recovery=expected_net_recovery,
        guardrail_result=verdict.result,
        guardrail_reason=verdict.reason,
        execution_result=execution_result,
        model_version=get_model().model_version,
        policy_version=POLICY_VERSION,
        idempotency_key=idem_key,
        final_outcome=final_outcome,
    )

    return {
        "transaction_id": transaction.id,
        "selected_strategy": final_strategy,
        "guardrail_result": verdict.result,
        "guardrail_reason": verdict.reason,
        "execution_result": execution_result,
        "final_outcome": final_outcome,
        "amount_recovered": amount_recovered,
        "expected_net_recovery": expected_net_recovery,
        "audit_log_id": audit_row.id,
    }

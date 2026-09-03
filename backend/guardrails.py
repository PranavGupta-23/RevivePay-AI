from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.config import (
    MAX_RETRY_ATTEMPTS, MAX_CONTACTS_PER_PERIOD, COOLDOWN_MINUTES_BETWEEN_ACTIONS,
    MIN_CONFIDENCE_FOR_AUTOMATION, CONTACT_STRATEGIES, RETRY_STRATEGIES,
)
from backend.decision_engine import CandidateResult
from backend.models_db import AuditLog, Transaction


@dataclass
class GuardrailVerdict:
    result: str 
    reason: str
    final_strategy: str


def make_idempotency_key(transaction_id: int, strategy: str, policy_version: str) -> str:
    raw = f"{transaction_id}:{strategy}:{policy_version}"
    return hashlib.sha256(raw.encode()).hexdigest()


def check_idempotency(db, transaction_id: int, strategy: str, policy_version: str) -> bool:
    """Returns True if this exact decision was already executed (duplicate)."""
    key = make_idempotency_key(transaction_id, strategy, policy_version)
    existing = db.query(AuditLog).filter_by(idempotency_key=key).first()
    return existing is not None


def evaluate_guardrails(
    db,
    transaction: Transaction,
    ranked_candidates: list[CandidateResult],
    consent_flag: bool,
    policy_version: str,
) -> GuardrailVerdict:
    """
    Walk the ranked candidate list top-down, applying guardrails, and return
    the first strategy that clears every rule (or an ESCALATE/ABSTAIN
    verdict if none do).
    """
    # Cooldown check (global, before even looking at strategy-specific rules)
    if transaction.last_action_at and COOLDOWN_MINUTES_BETWEEN_ACTIONS > 0:
        elapsed = datetime.utcnow() - transaction.last_action_at
        if elapsed < timedelta(minutes=COOLDOWN_MINUTES_BETWEEN_ACTIONS):
            return GuardrailVerdict(
                result="BLOCKED",
                reason=f"Cooldown active ({COOLDOWN_MINUTES_BETWEEN_ACTIONS} min between actions).",
                final_strategy="ABSTAIN",
            )

    for idx, candidate in enumerate(ranked_candidates):
        strategy = candidate.strategy
        reasons_blocked: list[str] = []

        if strategy in RETRY_STRATEGIES and transaction.retry_count >= MAX_RETRY_ATTEMPTS:
            reasons_blocked.append(
                f"Max retry attempts ({MAX_RETRY_ATTEMPTS}) already reached."
            )

        if strategy in CONTACT_STRATEGIES:
            if not consent_flag:
                reasons_blocked.append("Customer has opted out of contact (consent=False).")
            if transaction.contact_count >= MAX_CONTACTS_PER_PERIOD:
                reasons_blocked.append(
                    f"Max customer contacts ({MAX_CONTACTS_PER_PERIOD}) already reached."
                )

        if (
            transaction.failure_type == "INVALID_PAYMENT_METHOD"
            and strategy in RETRY_STRATEGIES
            and transaction.retry_count > 0
        ):
            reasons_blocked.append(
                "Invalid payment method cannot be fixed by blind retries."
            )

        if reasons_blocked:
            continue  

        if strategy != "ABSTAIN" and candidate.expected_net_recovery <= 0:
            return GuardrailVerdict(
                result="BLOCKED",
                reason=(
                    f"Expected net recovery for {strategy} is non-positive "
                    f"(₹{candidate.expected_net_recovery:,.2f}); abstaining instead."
                ),
                final_strategy="ABSTAIN",
            )

        if strategy != "ABSTAIN" and candidate.blended_probability < MIN_CONFIDENCE_FOR_AUTOMATION:
            return GuardrailVerdict(
                result="ESCALATED",
                reason=(
                    f"Confidence ({candidate.blended_probability:.0%}) below automation "
                    f"threshold ({MIN_CONFIDENCE_FOR_AUTOMATION:.0%}); escalating to human review."
                ),
                final_strategy="ESCALATE_TO_HUMAN",
            )

        result_label = "APPROVED" if idx == 0 else "REROUTED"
        reason = (
            "Top-ranked strategy passed all guardrails."
            if idx == 0
            else f"Top-ranked strategy(ies) were blocked; approved next-best candidate ({strategy})."
        )
        return GuardrailVerdict(result=result_label, reason=reason, final_strategy=strategy)

    # Nothing cleared -> escalate.
    return GuardrailVerdict(
        result="ESCALATED",
        reason="No candidate strategy cleared guardrails; escalating to human review.",
        final_strategy="ESCALATE_TO_HUMAN",
    )

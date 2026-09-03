from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.decision_engine import CandidateResult
from backend.models_db import AuditLog


def log_decision(
    db: Session,
    *,
    transaction_id: int,
    failure_type: str,
    candidates: list[CandidateResult],
    selected_strategy: str,
    expected_net_recovery: float,
    guardrail_result: str,
    guardrail_reason: str,
    execution_result: str,
    model_version: str,
    policy_version: str,
    idempotency_key: str,
    human_override: str = "",
    final_outcome: str = "",
) -> AuditLog:
    candidates_json = json.dumps(
        [
            {
                "strategy": c.strategy,
                "ml_probability": round(c.ml_probability, 4),
                "memory_probability": round(c.memory_probability, 4),
                "memory_attempts": c.memory_attempts,
                "blended_probability": round(c.blended_probability, 4),
                "intervention_cost": c.intervention_cost,
                "friction_penalty": c.friction_penalty,
                "expected_net_recovery": round(c.expected_net_recovery, 2),
            }
            for c in candidates
        ]
    )

    row = AuditLog(
        transaction_id=transaction_id,
        failure_type=failure_type,
        candidates_json=candidates_json,
        selected_strategy=selected_strategy,
        expected_net_recovery=expected_net_recovery,
        guardrail_result=guardrail_result,
        guardrail_reason=guardrail_reason,
        execution_result=execution_result,
        model_version=model_version,
        policy_version=policy_version,
        human_override=human_override,
        final_outcome=final_outcome,
        idempotency_key=idempotency_key,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

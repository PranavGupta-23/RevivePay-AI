from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agent import build_candidates
from backend.database import get_db
from backend.models_db import Customer, Transaction
from backend.schemas import CandidateStrategy, DecisionExplanation

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("/{transaction_id}", response_model=DecisionExplanation)
def get_decision(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    customer = db.query(Customer).filter(Customer.id == transaction.customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    bundle = build_candidates(db, transaction, customer)

    candidates_out = [
        CandidateStrategy(
            strategy=c.strategy,
            ml_probability=c.ml_probability,
            memory_probability=c.memory_probability,
            memory_attempts=c.memory_attempts,
            blended_probability=c.blended_probability,
            intervention_cost=c.intervention_cost,
            friction_penalty=c.friction_penalty,
            expected_net_recovery=c.expected_net_recovery,
        )
        for c in bundle.ranked_candidates
    ]

    return DecisionExplanation(
        transaction_id=transaction.id,
        amount=transaction.amount,
        failure_type=transaction.failure_type,
        candidates=candidates_out,
        recommended_strategy=bundle.recommended_strategy,
        reason=bundle.reason,
    )

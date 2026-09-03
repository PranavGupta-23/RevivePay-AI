from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models_db import HumanReview, Transaction, Customer
from backend.schemas import HumanReviewDecision
from backend.simulator import simulate_action
from backend.strategy_memory import update_memory

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue")
def review_queue(db: Session = Depends(get_db)):
    rows = (
        db.query(HumanReview)
        .filter(HumanReview.status == "PENDING")
        .order_by(HumanReview.created_at.desc())
        .all()
    )
    out = []
    for r in rows:
        txn = db.query(Transaction).filter(Transaction.id == r.transaction_id).first()
        out.append(
            {
                "id": r.id,
                "transaction_id": r.transaction_id,
                "amount": txn.amount if txn else None,
                "failure_type": txn.failure_type if txn else None,
                "reason": r.reason,
                "recommended_strategy": r.recommended_strategy,
                "status": r.status,
                "created_at": r.created_at,
            }
        )
    return out


@router.post("/{review_id}/decide")
def decide_review(review_id: int, payload: HumanReviewDecision, db: Session = Depends(get_db)):
    review = db.query(HumanReview).filter(HumanReview.id == review_id).first()
    if review is None:
        raise HTTPException(status_code=404, detail="Review item not found")
    if review.status != "PENDING":
        raise HTTPException(status_code=400, detail="Review item already decided")

    transaction = db.query(Transaction).filter(Transaction.id == review.transaction_id).first()
    customer = db.query(Customer).filter(Customer.id == transaction.customer_id).first()

    action = payload.action.upper()
    if action == "REJECT":
        review.status = "REJECTED"
        transaction.status = "ABSTAINED"
        outcome = "REJECTED_BY_HUMAN"

    elif action in ("APPROVE", "OVERRIDE"):
        strategy = (
            payload.override_strategy if action == "OVERRIDE" and payload.override_strategy
            else review.recommended_strategy
        )
        execution_result, success = simulate_action(transaction.failure_type, strategy)
        update_memory(db, transaction.failure_type, strategy, success)

        transaction.status = "RECOVERED" if success else "FAILED"
        review.status = "APPROVED"
        review.override_strategy = strategy
        outcome = execution_result
    else:
        raise HTTPException(status_code=400, detail="action must be APPROVE, REJECT, or OVERRIDE")

    review.reviewed_at = dt.datetime.utcnow()
    db.add(review)
    db.add(transaction)
    db.add(customer)
    db.commit()

    return {"review_id": review.id, "status": review.status, "outcome": outcome}

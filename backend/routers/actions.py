from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agent import execute_recovery
from backend.database import get_db
from backend.models_db import Customer, Transaction
from backend.schemas import ExecuteActionResponse

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/execute/{transaction_id}", response_model=ExecuteActionResponse)
def execute_action(transaction_id: int, db: Session = Depends(get_db)):
    """
    Runs DECIDE -> GUARDRAILS -> ACT -> MEASURE -> LEARN for one transaction.
    This is the endpoint the dashboard calls when the user clicks
    "Execute Recommended Strategy".
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if transaction.status not in ("FAILED",):
        raise HTTPException(
            status_code=400,
            detail=f"Transaction is already in status '{transaction.status}'.",
        )

    customer = db.query(Customer).filter(Customer.id == transaction.customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = execute_recovery(db, transaction, customer)
    return ExecuteActionResponse(**result)

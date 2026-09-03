from __future__ import annotations

import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.failure_normalizer import normalize_failure
from backend.models_db import Customer, Transaction
from backend.schemas import NewFailureRequest, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])

_PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet"]


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)
    if status:
        query = query.filter(Transaction.status == status)
    rows = (
        query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    )
    return rows


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    row = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return row


def _get_or_create_customer(db: Session, customer_ref: str | None) -> Customer:
    if customer_ref:
        existing = db.query(Customer).filter_by(customer_ref=customer_ref).first()
        if existing:
            return existing

    ref = customer_ref or f"CUST-{random.randint(100000, 999999)}"
    customer = Customer(
        customer_ref=ref,
        ltv_proxy=float(max(random.normalvariate(15000, 10000), 0)),
        subscription_status=random.choice(["NONE", "ACTIVE", "CHURNED"]),
        consent_flag=random.random() > 0.05,
        recent_activity_score=max(0.0, min(1.0, random.normalvariate(0.5, 0.2))),
        previous_failures_count=random.randint(0, 4),
        previous_successful_recoveries=random.randint(0, 2),
        previous_contacts_count=random.randint(0, 3),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.post("", response_model=TransactionOut)
def create_failed_transaction(payload: NewFailureRequest, db: Session = Depends(get_db)):
    """Ingest a new failed payment (OBSERVE step)."""
    customer = _get_or_create_customer(db, payload.customer_ref)
    failure_type = normalize_failure(payload.failure_raw_text)

    transaction = Transaction(
        customer_id=customer.id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        failure_raw_text=payload.failure_raw_text,
        failure_type=failure_type,
        status="FAILED",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction

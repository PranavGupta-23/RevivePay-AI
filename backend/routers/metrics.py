from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models_db import AuditLog, HumanReview, StrategyMemory, Transaction

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    failed_or_processed = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.status.in_(["FAILED", "RECOVERED", "ABSTAINED", "IN_REVIEW"]))
        .scalar()
        or 0
    )
    recovered_count = (
        db.query(func.count(Transaction.id)).filter(Transaction.status == "RECOVERED").scalar() or 0
    )
    revenue_at_risk = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(Transaction.status.in_(["FAILED", "IN_REVIEW", "ABSTAINED"]))
        .scalar()
        or 0.0
    )
    revenue_recovered = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(Transaction.status == "RECOVERED")
        .scalar()
        or 0.0
    )
    abstained_count = (
        db.query(func.count(Transaction.id)).filter(Transaction.status == "ABSTAINED").scalar() or 0
    )
    escalations = db.query(func.count(HumanReview.id)).scalar() or 0

    interventions = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.guardrail_result.in_(["APPROVED", "REROUTED"]))
        .scalar()
        or 0
    )

    recovery_rate = (recovered_count / failed_or_processed) if failed_or_processed else 0.0

    return {
        "total_transactions": total_transactions,
        "failed_transactions": failed_or_processed,
        "revenue_at_risk": revenue_at_risk,
        "revenue_recovered": revenue_recovered,
        "recovery_rate": recovery_rate,
        "interventions": interventions,
        "abstentions": abstained_count,
        "human_escalations": escalations,
        "recovered_count": recovered_count,
    }


@router.get("/strategy_performance")
def strategy_performance(db: Session = Depends(get_db)):
    rows = db.query(StrategyMemory).order_by(StrategyMemory.failure_type).all()
    return [
        {
            "failure_type": r.failure_type,
            "strategy": r.strategy,
            "attempts": r.attempts,
            "successes": r.successes,
            "success_rate": (r.successes / r.attempts) if r.attempts else None,
            "ema_rate": r.ema_rate,
        }
        for r in rows
    ]

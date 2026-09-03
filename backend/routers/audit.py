from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models_db import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_log(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    rows = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "transaction_id": r.transaction_id,
            "timestamp": r.timestamp,
            "failure_type": r.failure_type,
            "selected_strategy": r.selected_strategy,
            "expected_net_recovery": r.expected_net_recovery,
            "guardrail_result": r.guardrail_result,
            "guardrail_reason": r.guardrail_reason,
            "execution_result": r.execution_result,
            "model_version": r.model_version,
            "policy_version": r.policy_version,
            "human_override": r.human_override,
            "final_outcome": r.final_outcome,
        }
        for r in rows
    ]


@router.get("/{audit_id}")
def get_audit_entry(audit_id: int, db: Session = Depends(get_db)):
    row = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    result = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    result["candidates"] = json.loads(row.candidates_json) if row.candidates_json else []
    return result

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config import DRIFTED_SUCCESS_PROBABILITIES
from backend.database import get_db
from backend.models_db import StrategyMemory, StrategyMemoryHistory
from backend.schemas import SimulateOutcomesRequest, StrategyMemoryOut
from backend.simulator import simulate_bulk_outcomes
from backend.strategy_memory import update_memory
from ml.feature_engineering import FAILURE_TYPES, STRATEGIES

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=list[StrategyMemoryOut])
def list_memory(db: Session = Depends(get_db)):
    return db.query(StrategyMemory).order_by(StrategyMemory.failure_type).all()


@router.get("/history")
def memory_history(
    failure_type: str | None = None, strategy: str | None = None, db: Session = Depends(get_db)
):
    query = db.query(StrategyMemoryHistory)
    if failure_type:
        query = query.filter(StrategyMemoryHistory.failure_type == failure_type)
    if strategy:
        query = query.filter(StrategyMemoryHistory.strategy == strategy)
    rows = query.order_by(StrategyMemoryHistory.recorded_at.asc()).all()
    return [
        {
            "failure_type": r.failure_type,
            "strategy": r.strategy,
            "attempts": r.attempts,
            "successes": r.successes,
            "ema_rate": r.ema_rate,
            "recorded_at": r.recorded_at,
        }
        for r in rows
    ]


@router.post("/simulate")
def simulate_outcomes(payload: SimulateOutcomesRequest, db: Session = Depends(get_db)):
    """
    Feeds N synthetic outcomes directly into Strategy Memory for a given
    (failure_type, strategy) pair. This is the engine behind the
    'Simulate 100 New Outcomes' dashboard button and is what makes the
    system's adaptation visible: after enough biased outcomes, the blended
    probability -- and therefore future recommendations -- shifts.
    """
    if payload.failure_type not in FAILURE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown failure_type: {payload.failure_type}")
    if payload.strategy not in STRATEGIES:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {payload.strategy}")

    if payload.override_success_probability is not None:
        prob = payload.override_success_probability
    elif payload.use_drift_table:
        prob = DRIFTED_SUCCESS_PROBABILITIES.get(
            (payload.failure_type, payload.strategy), 0.5
        )
    else:
        prob = 0.5

    outcomes = simulate_bulk_outcomes(prob, payload.n)
    row = None
    for outcome in outcomes:
        row = update_memory(db, payload.failure_type, payload.strategy, outcome)

    return {
        "failure_type": payload.failure_type,
        "strategy": payload.strategy,
        "n_simulated": payload.n,
        "success_probability_used": prob,
        "new_attempts": row.attempts if row else 0,
        "new_successes": row.successes if row else 0,
        "new_ema_rate": row.ema_rate if row else None,
    }

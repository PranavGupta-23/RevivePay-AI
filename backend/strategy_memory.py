from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from backend.config import EMA_ALPHA, MEMORY_WEIGHT_HALFLIFE
from backend.models_db import StrategyMemory, StrategyMemoryHistory


def _get_or_create(db: Session, failure_type: str, strategy: str) -> StrategyMemory:
    row = (
        db.query(StrategyMemory)
        .filter_by(failure_type=failure_type, strategy=strategy)
        .first()
    )
    if row is None:
        row = StrategyMemory(
            failure_type=failure_type,
            strategy=strategy,
            attempts=0,
            successes=0,
            ema_rate=0.5,  
        )
        db.add(row)
        db.flush()
    return row


def get_memory_probability(
    db: Session, failure_type: str, strategy: str
) -> tuple[float, int]:
    row = (
        db.query(StrategyMemory)
        .filter_by(failure_type=failure_type, strategy=strategy)
        .first()
    )
    if row is None or row.attempts == 0:
        return 0.5, 0
    return row.ema_rate, row.attempts


def blend_weight(attempts: int) -> float:
    return attempts / (attempts + MEMORY_WEIGHT_HALFLIFE)


def blended_probability(ml_prob: float, memory_rate: float, attempts: int) -> float:
    w = blend_weight(attempts)
    return w * memory_rate + (1 - w) * ml_prob


def update_memory(
    db: Session, failure_type: str, strategy: str, success: bool
) -> StrategyMemory:
    """Update EMA + counters after one observed outcome, and log a history
    snapshot so the dashboard can chart the change over time."""
    row = _get_or_create(db, failure_type, strategy)
    row.attempts += 1
    row.successes += int(success)

    if row.attempts == 1:
        row.ema_rate = 1.0 if success else 0.0
    else:
        observed = 1.0 if success else 0.0
        row.ema_rate = EMA_ALPHA * observed + (1 - EMA_ALPHA) * row.ema_rate

    row.updated_at = dt.datetime.utcnow()
    db.add(row)

    history = StrategyMemoryHistory(
        failure_type=failure_type,
        strategy=strategy,
        attempts=row.attempts,
        successes=row.successes,
        ema_rate=row.ema_rate,
    )
    db.add(history)
    db.commit()
    db.refresh(row)
    return row


def list_all(db: Session) -> list[StrategyMemory]:
    return db.query(StrategyMemory).order_by(StrategyMemory.failure_type).all()

from __future__ import annotations
from dataclasses import dataclass
from backend.config import STRATEGY_COSTS
@dataclass

class CandidateResult:
    strategy: str
    ml_probability: float
    memory_probability: float
    memory_attempts: int
    blended_probability: float
    intervention_cost: float
    friction_penalty: float
    expected_net_recovery: float

def score_candidate(
    strategy: str,
    amount: float,
    ml_probability: float,
    memory_probability: float,
    memory_attempts: int,
    blended_probability: float,
) -> CandidateResult:
    costs = STRATEGY_COSTS.get(strategy, {"intervention_cost": 0.0, "friction_penalty": 0.0})
    intervention_cost = costs["intervention_cost"]
    friction_penalty = costs["friction_penalty"]

    if strategy == "ABSTAIN":
        expected_net_recovery = 0.0
    else:
        expected_net_recovery = (
            blended_probability * amount - intervention_cost - friction_penalty
        )

    return CandidateResult(
        strategy=strategy,
        ml_probability=ml_probability,
        memory_probability=memory_probability,
        memory_attempts=memory_attempts,
        blended_probability=blended_probability,
        intervention_cost=intervention_cost,
        friction_penalty=friction_penalty,
        expected_net_recovery=expected_net_recovery,
    )


def rank_candidates(candidates: list[CandidateResult]) -> list[CandidateResult]:
    return sorted(candidates, key=lambda c: c.expected_net_recovery, reverse=True)


def explain_choice(winner: CandidateResult, runner_up: CandidateResult | None) -> str:
    base = (
        f"{winner.strategy.replace('_', ' ').title()} has the highest expected net "
        f"recovery (₹{winner.expected_net_recovery:,.2f}), combining a blended success "
        f"probability of {winner.blended_probability:.0%} "
        f"(ML model: {winner.ml_probability:.0%}, strategy memory: "
        f"{winner.memory_probability:.0%} over {winner.memory_attempts} past attempts) "
        f"against an intervention cost of ₹{winner.intervention_cost:,.2f} and a "
        f"friction penalty of ₹{winner.friction_penalty:,.2f}."
    )
    if runner_up is not None:
        base += (
            f" The next-best option, {runner_up.strategy.replace('_', ' ').title()}, "
            f"trailed with an expected net recovery of ₹{runner_up.expected_net_recovery:,.2f}."
        )
    return base

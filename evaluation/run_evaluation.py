from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import STRATEGY_COSTS, CANDIDATE_STRATEGIES_BY_FAILURE, RANDOM_SEED, TEST_PATH  # noqa: E402
from backend.decision_engine import score_candidate, rank_candidates  # noqa: E402
from backend.guardrails import evaluate_guardrails  # noqa: E402
from backend.ml_model import get_model  # noqa: E402
from evaluation.baselines import (  # noqa: E402
    BASELINES, highest_historical_average,
)
from ml.generate_synthetic_data import true_success_probability  # noqa: E402


class InMemoryStrategyMemory:
    """A tiny, DB-free re-implementation of backend/strategy_memory.py's
    EMA logic, used only for this standalone evaluation script so it does
    not touch the live demo database."""

    def __init__(self, halflife: int = 20, alpha: float = 0.15):
        self.halflife = halflife
        self.alpha = alpha
        self.table: dict[tuple[str, str], dict] = {}

    def get(self, failure_type: str, strategy: str) -> tuple[float, int]:
        row = self.table.get((failure_type, strategy))
        if row is None or row["attempts"] == 0:
            return 0.5, 0
        return row["ema_rate"], row["attempts"]

    def blend(self, ml_prob: float, memory_rate: float, attempts: int) -> float:
        w = attempts / (attempts + self.halflife)
        return w * memory_rate + (1 - w) * ml_prob

    def update(self, failure_type: str, strategy: str, success: bool) -> None:
        key = (failure_type, strategy)
        row = self.table.setdefault(key, {"attempts": 0, "successes": 0, "ema_rate": 0.5})
        row["attempts"] += 1
        row["successes"] += int(success)
        if row["attempts"] == 1:
            row["ema_rate"] = 1.0 if success else 0.0
        else:
            observed = 1.0 if success else 0.0
            row["ema_rate"] = self.alpha * observed + (1 - self.alpha) * row["ema_rate"]

    def as_rows(self) -> list[dict]:
        return [
            {"failure_type": ft, "strategy": s, "attempts": v["attempts"],
             "successes": v["successes"], "ema_rate": v["ema_rate"]}
            for (ft, s), v in self.table.items()
        ]


def sample_outcome(row: pd.Series, strategy: str, rng: np.random.Generator) -> bool:
    prob = true_success_probability(
        failure_type=row["failure_type"],
        strategy=strategy,
        previous_contacts_count=int(row["previous_contacts_count"]),
        previous_failures_count=int(row["previous_failures_count"]),
        recent_activity_score=float(row["recent_activity_score"]),
        subscription_status=row["subscription_status"],
        rng=rng,
    )
    return bool(rng.random() < prob)


def run_arsa_policy(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Runs ARSA's full DECIDE -> GUARDRAIL -> ACT -> LEARN loop sequentially
    over the held-out set, using a fresh in-memory strategy memory so we can
    also observe how quickly it adapts."""
    model = get_model()
    memory = InMemoryStrategyMemory()
    results = []

    for _, row in df.iterrows():
        failure_type = row["failure_type"]
        candidate_strategies = CANDIDATE_STRATEGIES_BY_FAILURE.get(
            failure_type, CANDIDATE_STRATEGIES_BY_FAILURE["UNKNOWN"]
        )
        ml_probs = model.predict_for_strategies(
            amount=row["amount"],
            failure_type=failure_type,
            payment_method=row["payment_method"],
            subscription_status=row["subscription_status"],
            previous_failures_count=int(row["previous_failures_count"]),
            previous_successful_recoveries=int(row["previous_successful_recoveries"]),
            previous_contacts_count=int(row["previous_contacts_count"]),
            ltv_proxy=float(np.expm1(row["ltv_proxy_log"])),
            recent_activity_score=float(row["recent_activity_score"]),
            retry_count=0,
            candidate_strategies=candidate_strategies,
        )

        candidates = []
        for strategy in candidate_strategies:
            memory_rate, attempts = memory.get(failure_type, strategy)
            blended = memory.blend(ml_probs[strategy], memory_rate, attempts)
            candidates.append(
                score_candidate(strategy, row["amount"], ml_probs[strategy], memory_rate, attempts, blended)
            )
        ranked = rank_candidates(candidates)

        fake_txn = SimpleNamespace(
            retry_count=0, contact_count=0, last_action_at=None, failure_type=failure_type,
        )
        verdict = evaluate_guardrails(
            db=None, transaction=fake_txn, ranked_candidates=ranked,
            consent_flag=True, policy_version="eval",
        )
        strategy = verdict.final_strategy

        if strategy in ("ABSTAIN", "ESCALATE_TO_HUMAN"):
            success = False
        else:
            success = sample_outcome(row, strategy, rng)
            memory.update(failure_type, strategy, success)

        winning = next((c for c in ranked if c.strategy == strategy), None)
        expected_value = winning.expected_net_recovery if winning else 0.0
        costs = STRATEGY_COSTS.get(strategy, {"intervention_cost": 0, "friction_penalty": 0})

        results.append(
            {
                "failure_type": failure_type,
                "amount": row["amount"],
                "strategy": strategy,
                "success": success,
                "amount_recovered": row["amount"] if success else 0.0,
                "cost": costs["intervention_cost"] + costs["friction_penalty"] if strategy not in ("ABSTAIN", "ESCALATE_TO_HUMAN") else 0.0,
                "expected_net_recovery": expected_value,
            }
        )

    return pd.DataFrame(results)


def run_baseline_policy(df: pd.DataFrame, policy_fn, rng: np.random.Generator, adaptive: bool = False) -> pd.DataFrame:
    results = []
    memory = InMemoryStrategyMemory() if adaptive else None

    for _, row in df.iterrows():
        failure_type = row["failure_type"]
        if adaptive:
            strategy = policy_fn(failure_type, memory.as_rows())
        else:
            strategy = policy_fn(failure_type)

        if strategy == "ABSTAIN":
            success = False
        else:
            success = sample_outcome(row, strategy, rng)
            if adaptive:
                memory.update(failure_type, strategy, success)

        costs = STRATEGY_COSTS.get(strategy, {"intervention_cost": 0, "friction_penalty": 0})
        results.append(
            {
                "failure_type": failure_type,
                "amount": row["amount"],
                "strategy": strategy,
                "success": success,
                "amount_recovered": row["amount"] if success else 0.0,
                "cost": costs["intervention_cost"] + costs["friction_penalty"] if strategy != "ABSTAIN" else 0.0,
            }
        )
    return pd.DataFrame(results)


def summarize(name: str, results: pd.DataFrame) -> dict:
    revenue_at_risk = results["amount"].sum()
    revenue_recovered = results["amount_recovered"].sum()
    recovery_rate = results["success"].mean()
    total_cost = results["cost"].sum()
    interventions = (results["strategy"] != "ABSTAIN").sum()
    abstentions = (results["strategy"] == "ABSTAIN").sum()
    escalations = (results["strategy"] == "ESCALATE_TO_HUMAN").sum()
    cost_per_recovered_rupee = (total_cost / revenue_recovered) if revenue_recovered > 0 else float("nan")

    return {
        "policy": name,
        "n": len(results),
        "revenue_at_risk": round(revenue_at_risk, 2),
        "revenue_recovered": round(revenue_recovered, 2),
        "recovery_rate": round(recovery_rate, 4),
        "total_cost": round(total_cost, 2),
        "cost_per_recovered_rupee": round(cost_per_recovered_rupee, 4) if revenue_recovered > 0 else None,
        "interventions": int(interventions),
        "abstentions": int(abstentions),
        "escalations": int(escalations),
    }


def main() -> None:
    if not TEST_PATH.exists():
        raise FileNotFoundError(
            f"{TEST_PATH} not found. Run `python ml/train_model.py` first "
            "(it creates the held-out test split)."
        )

    df = pd.read_csv(TEST_PATH)
    rng_seed = RANDOM_SEED + 777

    summaries = []
    rng = np.random.default_rng(rng_seed)
    arsa_results = run_arsa_policy(df, rng)
    summaries.append(summarize("ARSA (adaptive)", arsa_results))
    for name, fn in BASELINES.items():
        rng = np.random.default_rng(rng_seed)
        baseline_results = run_baseline_policy(df, fn, rng, adaptive=False)
        summaries.append(summarize(name, baseline_results))
    rng = np.random.default_rng(rng_seed)
    hha_results = run_baseline_policy(
        df, highest_historical_average, rng, adaptive=True
    )
    summaries.append(summarize("Highest Historical Average", hha_results))

    summary_df = pd.DataFrame(summaries).set_index("policy")

    arsa_recovered = summary_df.loc["ARSA (adaptive)", "revenue_recovered"]
    do_nothing_recovered = summary_df.loc["Do Nothing", "revenue_recovered"]
    summary_df["recovery_lift_vs_do_nothing"] = (
        (summary_df["revenue_recovered"] - do_nothing_recovered) / max(summary_df["revenue_at_risk"].iloc[0], 1)
    ).round(4)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)

    print("\n" + "=" * 100)
    print("ARSA vs. Baselines — SYNTHETIC / SIMULATED evaluation on the held-out test set")
    print("(These are NOT real Razorpay production results.)")
    print("=" * 100 + "\n")
    print(summary_df)
    print(
        f"\nARSA recovers ₹{arsa_recovered:,.0f} of ₹{summary_df['revenue_at_risk'].iloc[0]:,.0f} "
        f"at risk, vs. ₹{do_nothing_recovered:,.0f} for Do Nothing."
    )

    out_path = Path(__file__).resolve().parent / "evaluation_results.csv"
    summary_df.to_csv(out_path)
    print(f"\nSaved results to {out_path}")


if __name__ == "__main__":
    main()

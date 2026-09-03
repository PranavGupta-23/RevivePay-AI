from backend.decision_engine import score_candidate, rank_candidates

def test_expected_net_recovery_formula():
    candidate = score_candidate(
        strategy="SEND_PAYMENT_LINK",
        amount=20000.0,
        ml_probability=0.80,
        memory_probability=0.80,
        memory_attempts=0,
        blended_probability=0.80,
    )
    assert round(candidate.expected_net_recovery, 2) == 15965.0

def test_abstain_always_zero_expected_value():
    candidate = score_candidate(
        strategy="ABSTAIN",
        amount=50000.0,
        ml_probability=0.99,
        memory_probability=0.99,
        memory_attempts=100,
        blended_probability=0.99,
    )
    assert candidate.expected_net_recovery == 0.0

def test_ranking_picks_highest_expected_value():
    a = score_candidate("RETRY_NOW", 10000, 0.30, 0.30, 0, 0.30)
    b = score_candidate("RETRY_LATER", 10000, 0.70, 0.70, 0, 0.70)
    ranked = rank_candidates([a, b])
    assert ranked[0].strategy == "RETRY_LATER"
    assert ranked[1].strategy == "RETRY_NOW"

def test_higher_cost_strategy_can_lose_to_lower_cost_lower_prob():
    cheap = score_candidate("RETRY_LATER", 5000, 0.50, 0.50, 0, 0.50)
    expensive = score_candidate("ESCALATE_TO_HUMAN", 5000, 0.50, 0.50, 0, 0.50)
    ranked = rank_candidates([cheap, expensive])
    assert ranked[0].strategy == "RETRY_LATER"

from backend.strategy_memory import (
    get_memory_probability, update_memory, blend_weight, blended_probability,
)

def test_unseen_pair_defaults_to_neutral_prior(db_session):
    rate, attempts = get_memory_probability(db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_NOW")
    assert attempts == 0
    assert rate == 0.5

def test_update_memory_increments_counters(db_session):
    update_memory(db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_LATER", True)
    update_memory(db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_LATER", False)
    rate, attempts = get_memory_probability(db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_LATER")
    assert attempts == 2

def test_ema_moves_toward_recent_observations(db_session):
    update_memory(db_session, "INSUFFICIENT_FUNDS", "RETRY_NOW", True)
    rate_after_1, _ = get_memory_probability(db_session, "INSUFFICIENT_FUNDS", "RETRY_NOW")
    for _ in range(30):
        update_memory(db_session, "INSUFFICIENT_FUNDS", "RETRY_NOW", False)
    rate_after_31, _ = get_memory_probability(db_session, "INSUFFICIENT_FUNDS", "RETRY_NOW")
    assert rate_after_31 < rate_after_1

def test_blend_weight_grows_with_attempts():
    w_low = blend_weight(1)
    w_high = blend_weight(500)
    assert w_high > w_low
    assert 0 <= w_low <= 1
    assert 0 <= w_high <= 1

def test_blended_probability_leans_on_ml_when_no_history():
    blended = blended_probability(ml_prob=0.30, memory_rate=0.90, attempts=0)
    assert abs(blended - 0.30) < 1e-9  

def test_adaptation_demo_strategy_preference_flips(db_session):
    ml_prob_retry_now = 0.32
    ml_prob_retry_later = 0.71
    mem_now, att_now = get_memory_probability(db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_NOW")
    mem_later, att_later = get_memory_probability(db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_LATER")
    blended_now = blended_probability(ml_prob_retry_now, mem_now, att_now)
    blended_later = blended_probability(ml_prob_retry_later, mem_later, att_later)
    assert blended_later > blended_now
    import random
    random.seed(1)
    for _ in range(150):
        update_memory(
            db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_NOW", random.random() < 0.68
        )
        update_memory(
            db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_LATER", random.random() < 0.45
        )

    mem_now, att_now = get_memory_probability(db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_NOW")
    mem_later, att_later = get_memory_probability(db_session, "TEMPORARY_NETWORK_FAILURE", "RETRY_LATER")
    blended_now_after = blended_probability(ml_prob_retry_now, mem_now, att_now)
    blended_later_after = blended_probability(ml_prob_retry_later, mem_later, att_later)

    assert blended_now_after > blended_later_after, (
        "Strategy memory should have adapted enough to flip the preference "
        "toward RETRY_NOW after sustained new evidence."
    )
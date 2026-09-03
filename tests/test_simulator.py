from backend.simulator import simulate_action, simulate_bulk_outcomes

def test_abstain_never_executes():
    result, success = simulate_action("TEMPORARY_NETWORK_FAILURE", "ABSTAIN")
    assert result == "NO_ACTION_TAKEN"
    assert success is False

def test_escalate_returns_pending_not_success():
    result, success = simulate_action("REPEATED_FAILURE", "ESCALATE_TO_HUMAN")
    assert result == "PENDING_HUMAN_REVIEW"
    assert success is False

def test_simulate_action_returns_bool_success_flag():
    result, success = simulate_action("TEMPORARY_NETWORK_FAILURE", "RETRY_LATER")
    assert isinstance(success, bool)
    assert result in ("SUCCESS", "FAILURE", "DELAYED_NO_RESULT_YET")

def test_bulk_outcomes_reproducible_rate():
    outcomes = simulate_bulk_outcomes(0.7, 2000)
    rate = sum(outcomes) / len(outcomes)
    assert 0.6 < rate < 0.8  # roughly matches requested probability
    assert all(isinstance(o, bool) for o in outcomes)

def test_bulk_outcomes_zero_probability():
    outcomes = simulate_bulk_outcomes(0.0, 100)
    assert not any(outcomes)

def test_bulk_outcomes_one_probability():
    outcomes = simulate_bulk_outcomes(1.0, 100)
    assert all(outcomes)
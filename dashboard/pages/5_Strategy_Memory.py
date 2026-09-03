from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard import api_client

st.set_page_config(page_title="Strategy Memory — RevivePay AI", page_icon="🧬", layout="wide")
st.title("🧬 Strategy Memory — Adaptation Demo")
st.caption("All data is synthetic/simulated.")

if not api_client.is_backend_up():
    st.error("Backend not reachable. Start it with `uvicorn backend.main:app --reload --port 8000`.")
    st.stop()

st.markdown(
    """
This page shows the **adaptive learning loop** in action. Strategy Memory
tracks a running exponential-moving-average (EMA) success rate for every
`(failure_type, strategy)` pair, based on real observed outcomes inside this
running system (in addition to, and blended with, the offline-trained ML
model). As more outcomes come in, the system trusts its own memory more and
the ML model less — so its recommendations can genuinely change over time.
"""
)

st.subheader("Current strategy memory")
memory_rows = api_client.list_memory()
if memory_rows:
    mem_df = pd.DataFrame(memory_rows)
    mem_display = mem_df.copy()
    mem_display["ema_rate"] = mem_display["ema_rate"].map(lambda x: f"{x:.1%}")
    st.dataframe(
        mem_display[["failure_type", "strategy", "attempts", "successes", "ema_rate"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No strategy memory yet — execute some recovery actions or simulate outcomes below.")

st.divider()
st.subheader("🔁 Simulate N New Outcomes (watch the system adapt)")
st.markdown(
    """
Pick a `(failure type, strategy)` pair and simulate a batch of new outcomes,
as if "the real world changed" (e.g. the payment gateway's retry success
rate shifted). This directly updates Strategy Memory — no need to create
individual transactions.
"""
)

FAILURE_TYPES = [
    "TEMPORARY_NETWORK_FAILURE", "INSUFFICIENT_FUNDS", "INVALID_PAYMENT_METHOD",
    "CHECKOUT_ABANDONED", "REPEATED_FAILURE", "UNKNOWN",
]
STRATEGIES = [
    "RETRY_NOW", "RETRY_LATER", "SEND_PAYMENT_LINK", "SEND_RECOVERY_MESSAGE",
    "REQUEST_PAYMENT_METHOD_UPDATE", "ESCALATE_TO_HUMAN", "ABSTAIN",
]

c1, c2, c3 = st.columns(3)
failure_type = c1.selectbox("Failure type", FAILURE_TYPES, index=0)
strategy = c2.selectbox("Strategy", STRATEGIES, index=0)
n = c3.number_input("Number of outcomes", min_value=10, max_value=2000, value=100, step=10)

use_drift = st.checkbox(
    "Use built-in 'environment drift' probabilities "
    "(e.g. TEMPORARY_NETWORK_FAILURE / RETRY_NOW jumps to 68%)",
    value=True,
)
override_prob = None
if not use_drift:
    override_prob = st.slider("Custom success probability to simulate", 0.0, 1.0, 0.5, 0.01)

if st.button(f"▶️ Simulate {int(n)} New Outcomes", type="primary"):
    result = api_client.simulate_outcomes(
        failure_type=failure_type,
        strategy=strategy,
        n=int(n),
        use_drift_table=use_drift,
        override_success_probability=override_prob,
    )
    st.success(
        f"Simulated {result['n_simulated']} outcomes at "
        f"{result['success_probability_used']:.0%} success probability. "
        f"New EMA rate for ({failure_type}, {strategy}): **{result['new_ema_rate']:.1%}** "
        f"over {result['new_attempts']} total attempts."
    )
    st.rerun()

st.divider()
st.subheader("📉 EMA over time (for a chosen pair)")
c4, c5 = st.columns(2)
hist_failure = c4.selectbox("Failure type (history)", FAILURE_TYPES, index=0, key="hist_ft")
hist_strategy = c5.selectbox("Strategy (history)", STRATEGIES, index=0, key="hist_strat")

history = api_client.memory_history(hist_failure, hist_strategy)
if history:
    hist_df = pd.DataFrame(history)
    st.line_chart(hist_df.set_index("attempts")["ema_rate"])
    st.caption(
        "X-axis = cumulative attempts observed for this pair. "
        "Watch this curve move after you simulate new outcomes above."
    )
else:
    st.info("No history yet for this pair. Simulate some outcomes above first.")

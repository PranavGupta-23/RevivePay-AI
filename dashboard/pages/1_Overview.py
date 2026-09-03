from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from dashboard import api_client

st.set_page_config(page_title="Overview — RevivePay AI", page_icon="📊", layout="wide")
st.title("📊 Overview")
st.caption("All figures are synthetic/simulated.")

if not api_client.is_backend_up():
    st.error("Backend not reachable. Start it with `uvicorn backend.main:app --reload --port 8000`.")
    st.stop()

metrics = api_client.overview_metrics()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Transactions", f"{metrics['total_transactions']:,}")
col2.metric("Failed / Processed", f"{metrics['failed_transactions']:,}")
col3.metric("Revenue at Risk", f"₹{metrics['revenue_at_risk']:,.0f}")
col4.metric("Revenue Recovered", f"₹{metrics['revenue_recovered']:,.0f}")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Recovery Rate", f"{metrics['recovery_rate']:.1%}")
col6.metric("Interventions", f"{metrics['interventions']:,}")
col7.metric("Abstentions", f"{metrics['abstentions']:,}")
col8.metric("Human Escalations", f"{metrics['human_escalations']:,}")

st.divider()
st.subheader("What these numbers mean")
st.markdown(
    """
- **Revenue at Risk** — total ₹ value of payments currently failed, in
  human review, or abstained on (i.e. not yet recovered).
- **Revenue Recovered** — total ₹ value of payments the agent successfully
  brought back via a simulated recovery action.
- **Recovery Rate** — recovered ÷ (failed + recovered + abstained + in-review).
- **Interventions** — number of times the agent actually took an action
  (as opposed to abstaining or escalating).

Use **Recovery Queue** to create new failed payments and watch these
numbers move.
"""
)

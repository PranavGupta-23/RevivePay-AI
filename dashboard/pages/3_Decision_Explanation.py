from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard import api_client

st.set_page_config(page_title="Decision Explanation — RevivePay AI", page_icon="🧠", layout="wide")
st.title("🧠 Decision Explanation")
st.caption("All data is synthetic/simulated.")

if not api_client.is_backend_up():
    st.error("Backend not reachable. Start it with `uvicorn backend.main:app --reload --port 8000`.")
    st.stop()

txn_id = st.number_input("Transaction ID", min_value=1, value=1, step=1)

if st.button("Explain decision", type="primary"):
    try:
        decision = api_client.get_decision(int(txn_id))
    except Exception as e:
        st.error(f"Could not load decision (does this transaction exist?): {e}")
        st.stop()

    st.markdown(f"### Transaction #{decision['transaction_id']}")
    c1, c2 = st.columns(2)
    c1.metric("Amount", f"₹{decision['amount']:,.2f}")
    c2.metric("Failure Type", decision["failure_type"])

    st.subheader("Candidate strategies (ranked)")
    df = pd.DataFrame(decision["candidates"])
    display_df = df.copy()
    display_df["ml_probability"] = display_df["ml_probability"].map(lambda x: f"{x:.1%}")
    display_df["memory_probability"] = display_df["memory_probability"].map(lambda x: f"{x:.1%}")
    display_df["blended_probability"] = display_df["blended_probability"].map(lambda x: f"{x:.1%}")
    display_df["intervention_cost"] = display_df["intervention_cost"].map(lambda x: f"₹{x:,.2f}")
    display_df["friction_penalty"] = display_df["friction_penalty"].map(lambda x: f"₹{x:,.2f}")
    display_df["expected_net_recovery"] = display_df["expected_net_recovery"].map(lambda x: f"₹{x:,.2f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.bar_chart(df.set_index("strategy")["expected_net_recovery"])

    st.success(f"### ✅ Recommended: {decision['recommended_strategy']}")
    st.markdown(f"**Reason:** {decision['reason']}")

    if st.button("▶️ Execute this recommendation"):
        result = api_client.execute_action(int(txn_id))
        st.json(result)

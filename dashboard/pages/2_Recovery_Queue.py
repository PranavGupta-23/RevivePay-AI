from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard import api_client

st.set_page_config(page_title="Recovery Queue — RevivePay AI", page_icon="🧾", layout="wide")
st.title("🧾 Recovery Queue")
st.caption("All data is synthetic/simulated.")

if not api_client.is_backend_up():
    st.error("Backend not reachable. Start it with `uvicorn backend.main:app --reload --port 8000`.")
    st.stop()

with st.expander("➕ Create a new failed payment", expanded=False):
    with st.form("new_failure_form"):
        c1, c2 = st.columns(2)
        amount = c1.number_input("Amount (₹)", min_value=100.0, value=15000.0, step=500.0)
        payment_method = c2.selectbox("Payment method", ["card", "upi", "netbanking", "wallet"])
        failure_text = st.text_input(
            "Failure description (messy text is fine — the normalizer will classify it)",
            value="issuer server was temporarily unavailable",
        )
        customer_ref = st.text_input("Customer ref (optional — leave blank to auto-create)", value="")
        submitted = st.form_submit_button("Create failed payment")
        if submitted:
            txn = api_client.create_failure(
                amount=amount,
                payment_method=payment_method,
                failure_raw_text=failure_text,
                customer_ref=customer_ref or None,
            )
            st.success(f"Created transaction #{txn['id']} — classified as **{txn['failure_type']}**")
            st.rerun()

st.subheader("Failed / at-risk payments")
status_filter = st.selectbox("Filter by status", ["FAILED", "RECOVERED", "ABSTAINED", "IN_REVIEW", "(all)"])
txns = api_client.list_transactions(status=None if status_filter == "(all)" else status_filter)

if not txns:
    st.info("No transactions yet. Create one above to get started.")
    st.stop()

df = pd.DataFrame(txns)
st.dataframe(
    df[["id", "amount", "payment_method", "failure_type", "status", "retry_count", "contact_count", "created_at"]],
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Inspect a transaction")
txn_id = st.number_input("Transaction ID", min_value=1, value=int(df["id"].iloc[0]), step=1)

if st.button("Load decision for this transaction"):
    try:
        decision = api_client.get_decision(int(txn_id))
        st.session_state["last_decision"] = decision
    except Exception as e:
        st.error(f"Could not load decision: {e}")

if "last_decision" in st.session_state and st.session_state["last_decision"]["transaction_id"] == txn_id:
    decision = st.session_state["last_decision"]
    st.markdown(f"**Amount:** ₹{decision['amount']:,.2f}  |  **Failure type:** {decision['failure_type']}")
    cand_df = pd.DataFrame(decision["candidates"])
    cand_df["blended_probability"] = cand_df["blended_probability"].map(lambda x: f"{x:.1%}")
    cand_df["expected_net_recovery"] = cand_df["expected_net_recovery"].map(lambda x: f"₹{x:,.0f}")
    st.dataframe(
        cand_df[["strategy", "blended_probability", "expected_net_recovery", "memory_attempts"]],
        use_container_width=True,
        hide_index=True,
    )
    st.success(f"✅ Recommended: **{decision['recommended_strategy']}**")
    st.caption(decision["reason"])

    if st.button("▶️ Execute Recommended Strategy", type="primary"):
        result = api_client.execute_action(int(txn_id))
        st.json(result)
        del st.session_state["last_decision"]
        st.rerun()

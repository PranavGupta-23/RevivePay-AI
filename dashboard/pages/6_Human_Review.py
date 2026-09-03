from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard import api_client

st.set_page_config(page_title="Human Review — RevivePay AI", page_icon="🧑‍⚖️", layout="wide")
st.title("🧑‍⚖️ Human Review Queue")
st.caption("Cases escalated by guardrails (low confidence, high risk, or repeatedly failed). Synthetic/simulated.")

if not api_client.is_backend_up():
    st.error("Backend not reachable. Start it with `uvicorn backend.main:app --reload --port 8000`.")
    st.stop()

queue = api_client.review_queue()

if not queue:
    st.info(
        "No pending reviews. Cases land here when the guardrail engine "
        "escalates due to low confidence or high risk — try creating a "
        "small/ambiguous failed payment on the Recovery Queue page."
    )
    st.stop()

df = pd.DataFrame(queue)
st.dataframe(
    df[["id", "transaction_id", "amount", "failure_type", "recommended_strategy", "reason", "created_at"]],
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Decide a case")
review_id = st.number_input("Review ID", min_value=1, value=int(df["id"].iloc[0]), step=1)

STRATEGIES = [
    "RETRY_NOW", "RETRY_LATER", "SEND_PAYMENT_LINK", "SEND_RECOVERY_MESSAGE",
    "REQUEST_PAYMENT_METHOD_UPDATE", "ESCALATE_TO_HUMAN", "ABSTAIN",
]

c1, c2, c3 = st.columns(3)
if c1.button("✅ Approve recommended strategy"):
    result = api_client.decide_review(int(review_id), "APPROVE")
    st.json(result)
    st.rerun()

if c2.button("❌ Reject (abstain)"):
    result = api_client.decide_review(int(review_id), "REJECT")
    st.json(result)
    st.rerun()

with c3:
    override_strategy = st.selectbox("Override strategy", STRATEGIES, key="override_select")
    if st.button("✏️ Override & execute"):
        result = api_client.decide_review(int(review_id), "OVERRIDE", override_strategy=override_strategy)
        st.json(result)
        st.rerun()

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard import api_client

st.set_page_config(page_title="Audit Log — RevivePay AI", page_icon="📜", layout="wide")
st.title("📜 Audit Log")
st.caption("Full, immutable decision trail. Synthetic/simulated.")

if not api_client.is_backend_up():
    st.error("Backend not reachable. Start it with `uvicorn backend.main:app --reload --port 8000`.")
    st.stop()

rows = api_client.list_audit(limit=500)
if not rows:
    st.info("No audit entries yet. Execute a recovery action from the Recovery Queue page.")
    st.stop()

df = pd.DataFrame(rows)
st.dataframe(
    df[
        [
            "id", "transaction_id", "timestamp", "failure_type", "selected_strategy",
            "expected_net_recovery", "guardrail_result", "execution_result",
            "final_outcome", "model_version", "policy_version",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Inspect one audit entry")
audit_id = st.number_input("Audit Log ID", min_value=1, value=int(df["id"].iloc[0]), step=1)
if st.button("Load full entry"):
    entry = api_client.get_audit_entry(int(audit_id))
    st.markdown(f"**Guardrail result:** {entry['guardrail_result']} — {entry['guardrail_reason']}")
    st.markdown(f"**Execution result:** {entry['execution_result']}  |  **Final outcome:** {entry['final_outcome']}")
    st.subheader("All candidates considered at decision time")
    cand_df = pd.DataFrame(entry["candidates"])
    st.dataframe(cand_df, use_container_width=True, hide_index=True)

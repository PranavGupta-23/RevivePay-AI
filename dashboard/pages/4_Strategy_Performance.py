from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard import api_client

st.set_page_config(page_title="Strategy Performance — RevivePay AI", page_icon="📈", layout="wide")
st.title("📈 Strategy Performance")
st.caption("Success rates per failure type / strategy, from the system's own strategy memory. Synthetic/simulated.")

if not api_client.is_backend_up():
    st.error("Backend not reachable. Start it with `uvicorn backend.main:app --reload --port 8000`.")
    st.stop()

rows = api_client.strategy_performance()
if not rows:
    st.info(
        "No strategy memory yet. Execute a few recovery actions from the "
        "**Recovery Queue** page, or use **Strategy Memory → Simulate N Outcomes**."
    )
    st.stop()

df = pd.DataFrame(rows)
df["success_rate"] = df["success_rate"].fillna(0.0)

for failure_type, group in df.groupby("failure_type"):
    st.subheader(failure_type)
    g = group.sort_values("ema_rate", ascending=False).copy()
    g_display = g.copy()
    g_display["success_rate"] = g_display["success_rate"].map(lambda x: f"{x:.1%}")
    g_display["ema_rate"] = g_display["ema_rate"].map(lambda x: f"{x:.1%}")
    st.dataframe(
        g_display[["strategy", "attempts", "successes", "success_rate", "ema_rate"]],
        use_container_width=True,
        hide_index=True,
    )
    st.bar_chart(g.set_index("strategy")["ema_rate"])
    st.divider()

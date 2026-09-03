from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dashboard import api_client

st.set_page_config(
    page_title="RevivePay AI — Adaptive Recovery Strategy Agent",
    page_icon="💳",
    layout="wide",
)

st.sidebar.title("💳 RevivePay AI")
st.sidebar.caption("Adaptive Recovery Strategy Agent")
st.sidebar.markdown(
    "**All data on this dashboard is synthetic / simulated.** "
    "Nothing here reflects real Razorpay production data or real money."
)

if not api_client.is_backend_up():
    st.error(
        "⚠️ Cannot reach the FastAPI backend at "
        f"`{api_client.BACKEND_URL}`.\n\n"
        "Start it first with:\n\n"
        "```powershell\nuvicorn backend.main:app --reload --port 8000\n```"
    )
    st.stop()

st.title("Adaptive Recovery Strategy Agent")
st.markdown(
    """
Use the pages in the left sidebar to explore RevivePay AI:

- **Overview** — headline recovery metrics
- **Recovery Queue** — failed payments awaiting a decision
- **Decision Explanation** — why the agent picked a given strategy
- **Strategy Performance** — success rates by failure type & strategy
- **Strategy Memory** — how the system adapts over time (the demo button lives here)
- **Human Review** — escalated cases needing a human decision
- **Audit Log** — full, immutable decision trail

**Core loop:** OBSERVE → DECIDE → ACT → MEASURE → LEARN → ADAPT
"""
)

st.info(
    "New to the demo? Go to **Recovery Queue** → create a new failed payment → "
    "open its **Decision Explanation** → **Execute Recommended Strategy** → "
    "then visit **Strategy Memory** and click **Simulate 100 New Outcomes** "
    "to watch the system adapt."
)

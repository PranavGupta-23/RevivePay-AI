from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers import actions, audit, decisions, memory, metrics, review, transactions

app = FastAPI(
    title="ARSA — Adaptive Recovery Strategy Agent",
    description=(
        "AI-powered revenue recovery backend for failed payments. "
        "All figures are synthetic/simulated — not real Razorpay production data."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root():
    return {
        "service": "ARSA backend",
        "status": "running",
        "docs": "/docs",
        "note": "All data is synthetic/simulated.",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(transactions.router)
app.include_router(decisions.router)
app.include_router(actions.router)
app.include_router(memory.router)
app.include_router(review.router)
app.include_router(audit.router)
app.include_router(metrics.router)

from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "arsa.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

MODEL_DIR = DATA_DIR / "models"
MODEL_PATH = MODEL_DIR / "model.pkl"
MODEL_METADATA_PATH = MODEL_DIR / "metadata.json"

RAW_DATA_PATH = DATA_DIR / "raw" / "synthetic_transactions.csv"
TRAIN_PATH = DATA_DIR / "processed" / "train.csv"
VAL_PATH = DATA_DIR / "processed" / "val.csv"
TEST_PATH = DATA_DIR / "processed" / "test.csv"

RANDOM_SEED = 42

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
LLM_MODEL = os.getenv("ARSA_LLM_MODEL", "claude-sonnet-4-6")
USE_LLM = bool(ANTHROPIC_API_KEY)

POLICY_VERSION = "policy-v1.0"
MODEL_VERSION = "model-v1.0"

STRATEGY_COSTS = {
    "RETRY_NOW": {"intervention_cost": 0.0, "friction_penalty": 5.0},
    "RETRY_LATER": {"intervention_cost": 0.0, "friction_penalty": 5.0},
    "SEND_PAYMENT_LINK": {"intervention_cost": 5.0, "friction_penalty": 30.0},
    "SEND_RECOVERY_MESSAGE": {"intervention_cost": 2.0, "friction_penalty": 20.0},
    "REQUEST_PAYMENT_METHOD_UPDATE": {"intervention_cost": 3.0, "friction_penalty": 40.0},
    "ESCALATE_TO_HUMAN": {"intervention_cost": 60.0, "friction_penalty": 10.0},
    "ABSTAIN": {"intervention_cost": 0.0, "friction_penalty": 0.0},
}

CANDIDATE_STRATEGIES_BY_FAILURE = {
    "TEMPORARY_NETWORK_FAILURE": [
        "RETRY_NOW", "RETRY_LATER", "SEND_PAYMENT_LINK",
        "SEND_RECOVERY_MESSAGE", "ABSTAIN",
    ],
    "INSUFFICIENT_FUNDS": [
        "RETRY_LATER", "SEND_RECOVERY_MESSAGE", "SEND_PAYMENT_LINK",
        "RETRY_NOW", "ABSTAIN",
    ],
    "INVALID_PAYMENT_METHOD": [
        "REQUEST_PAYMENT_METHOD_UPDATE", "SEND_PAYMENT_LINK",
        "SEND_RECOVERY_MESSAGE", "ABSTAIN",
    ],
    "CHECKOUT_ABANDONED": [
        "SEND_PAYMENT_LINK", "SEND_RECOVERY_MESSAGE", "RETRY_LATER", "ABSTAIN",
    ],
    "REPEATED_FAILURE": [
        "ESCALATE_TO_HUMAN", "REQUEST_PAYMENT_METHOD_UPDATE", "ABSTAIN",
    ],
    "UNKNOWN": [
        "SEND_RECOVERY_MESSAGE", "ESCALATE_TO_HUMAN", "ABSTAIN",
    ],
}

CONTACT_STRATEGIES = {
    "SEND_PAYMENT_LINK", "SEND_RECOVERY_MESSAGE", "REQUEST_PAYMENT_METHOD_UPDATE",
}
RETRY_STRATEGIES = {"RETRY_NOW", "RETRY_LATER"}

MAX_RETRY_ATTEMPTS = 3
MAX_CONTACTS_PER_PERIOD = 3
COOLDOWN_MINUTES_BETWEEN_ACTIONS = 0  
MIN_CONFIDENCE_FOR_AUTOMATION = 0.20
HIGH_VALUE_THRESHOLD = 25000.0
HIGH_RISK_REPEATED_FAILURES = 3

MEMORY_WEIGHT_HALFLIFE = 20  
EMA_ALPHA = 0.15  

DRIFTED_SUCCESS_PROBABILITIES = {
    ("TEMPORARY_NETWORK_FAILURE", "RETRY_NOW"): 0.68,
    ("TEMPORARY_NETWORK_FAILURE", "RETRY_LATER"): 0.45,
    ("INSUFFICIENT_FUNDS", "RETRY_NOW"): 0.55,
    ("INSUFFICIENT_FUNDS", "RETRY_LATER"): 0.30,
}

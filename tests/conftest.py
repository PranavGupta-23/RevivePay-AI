from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend import models_db  # noqa: F401  ensure models are registered

@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture()
def sample_customer(db_session):
    from backend.models_db import Customer

    customer = Customer(
        customer_ref="CUST-TEST-1",
        ltv_proxy=20000.0,
        subscription_status="ACTIVE",
        consent_flag=True,
        recent_activity_score=0.6,
        previous_failures_count=1,
        previous_successful_recoveries=1,
        previous_contacts_count=0,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer

@pytest.fixture()
def sample_transaction(db_session, sample_customer):
    from backend.models_db import Transaction

    txn = Transaction(
        customer_id=sample_customer.id,
        amount=15000.0,
        payment_method="card",
        failure_raw_text="issuer server was temporarily unavailable",
        failure_type="TEMPORARY_NETWORK_FAILURE",
        status="FAILED",
    )
    db_session.add(txn)
    db_session.commit()
    db_session.refresh(txn)
    return txn
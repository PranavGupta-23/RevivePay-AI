# RevivePay AI

## Adaptive AI for Payment Revenue Recovery

RevivePay AI is an adaptive AI-powered revenue recovery system that intelligently selects the most effective recovery strategy for failed payments.

Instead of blindly retrying failed payments, RevivePay AI analyzes the failure context, predicts the probability of success for different recovery strategies, considers expected net recovery, applies safety guardrails, and learns from previous recovery outcomes.

**Core Loop:** OBSERVE → DECIDE → ACT → MEASURE → LEARN → ADAPT

## Problem

Failed payments represent direct revenue risk for businesses. Traditional recovery systems often rely on fixed rules such as retrying every failed payment, retrying after a fixed delay, or using the same recovery action for different failure types.

Different payment failures may require different recovery strategies.

For example:
- Temporary network failures may benefit from a retry.
- Invalid payment methods may require a payment method update.
- Repeated failures may require human intervention.
- Some recovery attempts may not be economically justified.

RevivePay AI treats payment recovery as a decision-making and optimization problem rather than a simple retry mechanism.

## Solution

RevivePay AI evaluates multiple possible recovery strategies for each failed payment and selects the strategy with the highest expected net recovery while respecting safety constraints.

The system combines:
- Failure classification
- Machine learning
- Historical strategy performance
- Expected revenue calculations
- Adaptive strategy memory
- Safety guardrails
- Human review
- Simulated recovery execution
- Audit logging

Recovery outcomes are fed back into the system so that future decisions can adapt to observed results.

## How It Works

A failed payment passes through the following process:

```text
Failed Payment
      |
      v
Failure Normalization
      |
      v
Candidate Recovery Strategies
      |
      v
ML Success Probability Prediction
      |
      v
Strategy Memory
      |
      v
Decision Engine
      |
      v
Safety Guardrails
      |
      +------------------> Human Review
      |
      v
Recovery Action
      |
      v
Simulated Outcome
      |
      v
Measure Recovery
      |
      v
Update Strategy Memory
      |
      v
Future Decisions Adapt
```

The system follows the loop:

**OBSERVE → DECIDE → ACT → MEASURE → LEARN → ADAPT**

## AI Decision Engine

For each failed payment, RevivePay AI evaluates candidate recovery strategies.

The machine learning model estimates the probability of successful recovery based on the payment context, failure type, and selected strategy.

The Decision Engine then calculates:

**Expected Net Recovery = (P(success) × Payment Amount) − Intervention Cost − Friction Penalty**

The strategy with the strongest expected outcome is selected, provided that it satisfies the system's guardrails.

This means the system does not simply ask:

> "Should we retry?"

It asks:

> "Which recovery strategy is most likely to recover this revenue, and is taking that action justified?"

## Recovery Strategies

The system can evaluate strategies such as:

| Strategy | Example Use Case |
|---|---|
| `RETRY_NOW` | Immediate retry for potentially temporary failures |
| `RETRY_LATER` | Delayed retry when an immediate attempt may be less effective |
| `REQUEST_PAYMENT_METHOD_UPDATE` | Payment method appears invalid or unusable |
| `ESCALATE_TO_HUMAN` | Repeated or uncertain failures |
| `DO_NOTHING` | Recovery action is not justified |

The strategy set can be extended as additional recovery methods are introduced.

## Adaptive Strategy Memory

RevivePay AI does not rely only on the initial ML prediction.

The system maintains historical performance for combinations of failure type and recovery strategy.

For example, if `RETRY_LATER` consistently performs well for a particular failure type, its historical performance influences future decisions.

As new recovery outcomes are observed, the strategy memory is updated. This allows the system to adapt when recovery patterns change over time.

The adaptive behavior can be demonstrated by changing the observed outcomes for a particular failure type and observing the recommended strategy change accordingly.

## Safety Guardrails

Revenue recovery should not become uncontrolled automation.

RevivePay AI includes guardrails that can prevent or modify recovery actions based on factors such as:
- Maximum retry limits
- Contact limits
- Cooldown requirements
- Customer consent and do-not-contact conditions
- Confidence thresholds
- Negative expected recovery
- Invalid payment conditions
- Idempotency protection
- Human escalation

If a recovery action is not sufficiently justified, the system can abstain instead of acting.

**A good recovery system should know when not to act.**

## Human Review

Not every payment failure should be handled automatically.

RevivePay AI provides a human review path for cases where:
- Failures are repeated
- Confidence is low
- Additional judgment is required
- Automated recovery should be escalated

This creates a hybrid workflow in which high-confidence and safe decisions can proceed through the automated pipeline while uncertain cases can be reviewed by a human.

## Recovery Simulator

RevivePay AI includes a deterministic payment recovery simulator for development and evaluation.

The simulator allows recovery strategies to be tested without interacting with a real payment gateway.

It provides:
- Controlled recovery outcomes
- Reproducible experiments
- Strategy comparisons
- Adaptive learning demonstrations
- Safe development without real financial transactions

No real payment transactions are performed by this prototype.

## Evaluation

The system was evaluated using synthetic payment transaction data.

The machine learning model achieved a test ROC-AUC of approximately **0.742**.

In a simulated revenue recovery evaluation, RevivePay AI recovered **54.7% of at-risk revenue** compared with several baseline strategies:

| Strategy | Simulated Revenue Recovered |
|---|---:|
| **RevivePay AI** | **54.7%** |
| Highest Historical Average | 48.8% |
| Always Retry | 39.7% |
| Fixed Strategy | 31.3% |
| Do Nothing | 0.0% |

These results are based on synthetic data and a simulated recovery environment. They should not be interpreted as real-world or production performance.

## Synthetic Data

The project uses synthetic transaction data for development and evaluation.

The generated data includes payment-related attributes such as:
- Payment amount
- Failure type
- Payment method
- Subscription status
- Previous failures
- Recovery strategy
- Recovery outcome

Synthetic data allows the complete decision-making pipeline to be tested without exposing real customer or payment information.

## Architecture

The system consists of the following major components:

**Failure Normalizer**  
Normalizes and classifies payment failure information into a consistent failure type.

**ML Probability Model**  
Estimates the probability of successful recovery for candidate strategies.

**Strategy Memory**  
Stores historical recovery performance and allows the system to adapt based on observed outcomes.

**Decision Engine**  
Calculates expected net recovery and selects the most appropriate strategy.

**Guardrails**  
Apply safety and operational constraints before an action can be executed.

**Recovery Simulator**  
Provides controlled and reproducible recovery outcomes for testing.

**Human Review**  
Provides an escalation path for uncertain or higher-risk decisions.

**Audit Logger**  
Records recovery decisions and outcomes for traceability.

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic

### AI and Machine Learning
- Scikit-learn
- Logistic Regression
- Feature Engineering
- Adaptive Strategy Memory
- Probability-based Decision Making

### AI Assistance
- Anthropic API integration for failure classification and advisory functionality when configured

### Dashboard
- Streamlit
- Python

### Testing and Evaluation
- Pytest
- Synthetic Transaction Generation
- Recovery Simulation
- Baseline Comparison
- ROC-AUC Evaluation

## Project Structure

```text
RevivePay-AI/
|
├── backend/
|   ├── routers/
|   ├── agent.py
|   ├── audit_logger.py
|   ├── config.py
|   ├── database.py
|   ├── decision_engine.py
|   ├── failure_normalizer.py
|   ├── guardrails.py
|   ├── llm_client.py
|   ├── ml_model.py
|   ├── models_db.py
|   ├── schemas.py
|   ├── simulator.py
|   └── strategy_memory.py
|
├── dashboard/
|   ├── pages/
|   ├── api_client.py
|   └── app.py
|
├── evaluation/
|   ├── baselines.py
|   └── run_evaluation.py
|
├── ml/
|   ├── feature_engineering.py
|   ├── generate_synthetic_data.py
|   └── train_model.py
|
├── scripts/
|   ├── setup_windows.ps1
|   ├── run_backend.ps1
|   ├── run_dashboard.ps1
|   └── run_all_pipeline.ps1
|
├── tests/
|   ├── conftest.py
|   ├── test_decision_engine.py
|   ├── test_guardrails.py
|   ├── test_integration_flow.py
|   ├── test_simulator.py
|   └── test_strategy_memory.py
|
└── requirements.txt
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/PranavGupta-23/RevivePay-AI.git
cd RevivePay-AI
```

### 2. Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv RevivePay_AI
```

Activate the environment:

```powershell
.\RevivePay_AI\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file if you want to enable the optional LLM functionality.

Example:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

Never commit your real `.env` file or API keys to GitHub.

The system can operate using its deterministic fallback behavior when an API key is not configured.

### 5. Generate project data and train the model

The project includes scripts for generating synthetic transaction data and training the ML model.

The Windows setup script can be used to prepare the local environment:

```powershell
.\scripts\setup_windows.ps1
```

## Running the Application

### Start the FastAPI Backend

```powershell
.\scripts\run_backend.ps1
```

The backend runs locally on `http://localhost:8000`.

FastAPI documentation is available at `http://localhost:8000/docs`.

### Start the Streamlit Dashboard

Open another terminal, activate the virtual environment, and run:

```powershell
.\scripts\run_dashboard.ps1
```

The dashboard runs locally on `http://localhost:8501`.

## Running Tests

Run the complete test suite with:

```powershell
pytest
```

The project includes tests for:
- Decision Engine
- Guardrails
- Strategy Memory
- Recovery Simulator
- End-to-end integration flow

## Running Evaluation

The evaluation module compares RevivePay AI against baseline recovery strategies.

```powershell
python evaluation/run_evaluation.py
```

The evaluation includes comparisons against approaches such as:
- Always Retry
- Fixed Strategy
- Historical Average
- Do Nothing

## Security and Data Handling

This repository is designed as a prototype and evaluation system.

It uses synthetic payment data and a simulated recovery environment. The current project does not process real payment transactions.

A production deployment would require additional work around:
- Authentication and authorization
- Secure secret management
- Encryption
- Payment-provider integration
- Data privacy
- Audit integrity
- Rate limiting
- Monitoring
- Compliance requirements
- Production-grade payment security

Real card numbers, CVV values, passwords, API keys, or other sensitive credentials should never be stored in the repository.

## Current Limitations

RevivePay AI is currently a prototype and evaluation system.

Current limitations include:
- Synthetic transaction data
- Simulated payment outcomes
- Baseline ML model
- Local SQLite database
- Limited recovery strategy set
- No production payment gateway execution
- No production-scale infrastructure
- Prototype-level security and authentication

The evaluation results demonstrate the behavior of the system in a controlled environment rather than guaranteed real-world revenue recovery.

## Future Improvements

Potential future improvements include:
- Integration with real payment gateways
- More advanced ML models
- Contextual bandits or reinforcement learning for strategy optimization
- Customer-level recovery personalization
- Better time-to-retry optimization
- Multi-channel recovery workflows
- Production-grade event streaming
- Advanced experimentation and A/B testing
- Automated strategy discovery
- Real-time monitoring and alerting
- Stronger fraud and abuse controls
- Production authentication and authorization
- Scalable cloud deployment

## Buildathon Context

RevivePay AI was developed as an AI Revenue Recovery solution for the Razorpay AI Buildathon.

The core objective is to demonstrate how an AI-driven system can:

1. Detect revenue at risk
2. Understand the payment failure
3. Select an appropriate recovery intervention
4. Execute a bounded recovery workflow
5. Measure the outcome
6. Learn from the result
7. Adapt future recovery decisions

## Author

**Pranav Gupta**

Computer Science Engineering Student

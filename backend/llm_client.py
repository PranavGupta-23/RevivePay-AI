from __future__ import annotations

from backend.config import ANTHROPIC_API_KEY, USE_LLM, LLM_MODEL
from ml.feature_engineering import FAILURE_TYPES

_KEYWORD_RULES: list[tuple[str, str]] = [
    ("network", "TEMPORARY_NETWORK_FAILURE"),
    ("timeout", "TEMPORARY_NETWORK_FAILURE"),
    ("unavailable", "TEMPORARY_NETWORK_FAILURE"),
    ("temporarily", "TEMPORARY_NETWORK_FAILURE"),
    ("issuer", "TEMPORARY_NETWORK_FAILURE"),
    ("insufficient", "INSUFFICIENT_FUNDS"),
    ("balance", "INSUFFICIENT_FUNDS"),
    ("funds", "INSUFFICIENT_FUNDS"),
    ("expired", "INVALID_PAYMENT_METHOD"),
    ("invalid card", "INVALID_PAYMENT_METHOD"),
    ("invalid payment", "INVALID_PAYMENT_METHOD"),
    ("declined by issuer", "INVALID_PAYMENT_METHOD"),
    ("blocked card", "INVALID_PAYMENT_METHOD"),
    ("abandon", "CHECKOUT_ABANDONED"),
    ("cart", "CHECKOUT_ABANDONED"),
    ("did not complete", "CHECKOUT_ABANDONED"),
    ("repeated", "REPEATED_FAILURE"),
    ("multiple failed", "REPEATED_FAILURE"),
    ("again failed", "REPEATED_FAILURE"),
]


def _rule_based_classify(text: str) -> str:
    lowered = text.lower()
    for keyword, label in _KEYWORD_RULES:
        if keyword in lowered:
            return label
    return "UNKNOWN"


def classify_failure_text(text: str) -> str:
    """Standardize a raw failure description into a FailureType.
    Falls back to keyword rules whenever no API key is configured or the
    LLM call fails for any reason."""
    if not USE_LLM:
        return _rule_based_classify(text)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = (
            "Classify the following payment failure description into EXACTLY "
            f"one of these categories: {', '.join(FAILURE_TYPES)}.\n"
            "Respond with ONLY the category name, nothing else.\n\n"
            f"Description: \"{text}\""
        )
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        for label in FAILURE_TYPES:
            if label in raw:
                return label
        return _rule_based_classify(text)
    except Exception:
        # Never let an LLM outage break the pipeline.
        return _rule_based_classify(text)


_TEMPLATE_MESSAGES = {
    "RETRY_NOW": "We're retrying your recent payment of ₹{amount:,.2f} now — no action needed.",
    "RETRY_LATER": "We'll automatically retry your payment of ₹{amount:,.2f} shortly. No action needed.",
    "SEND_PAYMENT_LINK": "Your payment of ₹{amount:,.2f} didn't go through. Complete it securely here: {link}",
    "SEND_RECOVERY_MESSAGE": "We noticed an issue with your recent payment of ₹{amount:,.2f}. Please check your order and try again.",
    "REQUEST_PAYMENT_METHOD_UPDATE": "Your payment method couldn't be charged ₹{amount:,.2f}. Please update your payment details: {link}",
    "ESCALATE_TO_HUMAN": "Our support team is reviewing your recent payment of ₹{amount:,.2f} and will reach out shortly.",
    "ABSTAIN": "",
}


def generate_customer_message(strategy: str, amount: float) -> str:
    template = _TEMPLATE_MESSAGES.get(strategy, "")
    fallback = template.format(amount=amount, link="https://pay.example.com/recover/DEMO")

    if not USE_LLM or strategy == "ABSTAIN":
        return fallback

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = (
            "Write ONE short, friendly, professional customer-facing SMS/email "
            f"line (under 200 characters) telling the customer we are taking the "
            f"following already-decided recovery action: {strategy}, for a "
            f"payment of ₹{amount:,.2f}. Do not mention internal system names. "
            "Do not invent a discount or promise anything not stated."
        )
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        return text or fallback
    except Exception:
        return fallback

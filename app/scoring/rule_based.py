"""Rule-based risk scoring: weighted combination of fraud indicators."""
from app.config import settings


WEIGHTS = {
    "velocity": 0.25,
    "geographic": 0.25,
    "amount": 0.15,
    "card_testing": 0.20,
    "collusion": 0.05,
    "ato": 0.05,
    "fraud_ring": 0.05,
}


def calculate_rule_based_score(indicators: dict[str, float]) -> tuple[int, str]:
    """
    Calculate weighted risk score from individual indicator scores.
    Returns (score 0-100, risk_level).
    """
    weighted_score = 0
    for indicator, weight in WEIGHTS.items():
        score = indicators.get(f"{indicator}_score", 0)
        weighted_score += score * weight

    risk_score = min(int(round(weighted_score)), 100)

    # If any single indicator is extremely high, boost the score
    max_indicator = max(indicators.values()) if indicators else 0
    if max_indicator >= 90:
        risk_score = max(risk_score, 80)
    elif max_indicator >= 70:
        risk_score = max(risk_score, 65)

    # Count how many strong indicators triggered (score > 20)
    strong_triggered = sum(1 for v in indicators.values() if v >= 20)
    if strong_triggered >= 3:
        risk_score = max(risk_score, 70)
    elif strong_triggered >= 2:
        risk_score = max(risk_score, 55)

    risk_score = min(risk_score, 100)

    if risk_score >= settings.high_risk_threshold:
        risk_level = "high_risk"
    elif risk_score >= settings.low_risk_threshold:
        risk_level = "medium_risk"
    else:
        risk_level = "low_risk"

    return risk_score, risk_level

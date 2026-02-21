"""Hybrid scoring: combines rule-based and ML scores."""
from app.scoring.rule_based import calculate_rule_based_score
from app.scoring.ml_model import predict_risk, extract_features, is_model_trained
from app.config import settings


def calculate_hybrid_score(transaction: dict, indicators: dict) -> tuple[int, str, float | None]:
    """
    Calculate hybrid risk score combining rule-based and ML scores.
    Returns (final_score 0-100, risk_level, ml_score or None).
    """
    # Rule-based score
    rule_score, _ = calculate_rule_based_score(indicators)

    # ML score (if model trained)
    ml_score = None
    if is_model_trained():
        features = extract_features(transaction, indicators)
        ml_score = predict_risk(features)

    # Hybrid combination
    if ml_score is not None:
        final_score = int(round(0.4 * rule_score + 0.6 * ml_score))
    else:
        final_score = rule_score

    final_score = min(max(final_score, 0), 100)

    # Determine risk level
    if final_score >= settings.high_risk_threshold:
        risk_level = "high_risk"
    elif final_score >= settings.low_risk_threshold:
        risk_level = "medium_risk"
    else:
        risk_level = "low_risk"

    return final_score, risk_level, ml_score

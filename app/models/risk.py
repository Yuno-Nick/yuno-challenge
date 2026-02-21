from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    low_risk = "low_risk"
    medium_risk = "medium_risk"
    high_risk = "high_risk"


class FraudIndicators(BaseModel):
    velocity_score: float = 0.0
    geographic_score: float = 0.0
    amount_score: float = 0.0
    card_testing_score: float = 0.0
    collusion_score: float = 0.0
    ato_score: float = 0.0
    fraud_ring_score: float = 0.0
    ml_score: Optional[float] = None
    triggered_rules: list[str] = []


class RiskAssessment(BaseModel):
    transaction_id: str
    risk_score: int
    risk_level: str
    velocity_score: float = 0.0
    geographic_score: float = 0.0
    amount_score: float = 0.0
    card_testing_score: float = 0.0
    collusion_score: float = 0.0
    ato_score: float = 0.0
    fraud_ring_score: float = 0.0
    ml_score: Optional[float] = None
    triggered_rules: list[str] = []
    processed_at: Optional[datetime] = None


class DashboardMetrics(BaseModel):
    total_transactions: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    fraud_rate: float = 0.0
    total_amount_at_risk: float = 0.0
    transactions_today: int = 0
    avg_risk_score: float = 0.0

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    completed = "completed"
    pending = "pending"
    failed = "failed"
    refunded = "refunded"


class TransactionCreate(BaseModel):
    transaction_id: str
    timestamp: datetime
    user_id: str
    driver_id: str
    card_last4: str
    device_id: str
    pickup_city: str
    pickup_country: str
    pickup_lat: float
    pickup_lng: float
    dropoff_city: str
    dropoff_lat: float
    dropoff_lng: float
    distance_km: float
    duration_minutes: int
    amount: float
    currency: str
    payment_status: str = "completed"
    is_fraudulent: bool = False


class TransactionDB(TransactionCreate):
    id: Optional[str] = None
    created_at: Optional[datetime] = None


class TransactionBatch(BaseModel):
    transactions: list[TransactionCreate]

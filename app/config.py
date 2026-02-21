import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    api_url: str = os.getenv("API_URL", "http://localhost:8000")

    # Risk thresholds
    low_risk_threshold: int = 30
    high_risk_threshold: int = 60

    # Pipeline settings
    batch_size: int = 10
    batch_interval_seconds: int = 3

    # Fraud detection thresholds
    velocity_1h_threshold: int = 3
    velocity_24h_threshold: int = 15
    impossible_speed_kmh: float = 900.0
    suspicious_speed_kmh: float = 500.0
    amount_zscore_high: float = 3.0
    amount_zscore_medium: float = 2.0
    card_testing_small_count: int = 3
    card_testing_multiplier: float = 10.0
    collusion_high_threshold: int = 8
    collusion_medium_threshold: int = 5

    class Config:
        env_file = ".env"


settings = Settings()

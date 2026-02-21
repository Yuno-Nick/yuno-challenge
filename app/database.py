from supabase import create_client, Client
from app.config import settings
from typing import Optional
import json

_client: Optional[Client] = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def insert_transactions(transactions: list[dict]) -> list[dict]:
    client = get_supabase()
    result = client.table("transactions").insert(transactions).execute()
    return result.data


def insert_risk_assessments(assessments: list[dict]) -> list[dict]:
    client = get_supabase()
    for a in assessments:
        if "triggered_rules" in a and isinstance(a["triggered_rules"], list):
            a["triggered_rules"] = json.dumps(a["triggered_rules"])
    result = client.table("risk_assessments").insert(assessments).execute()
    return result.data


def get_transactions(limit: int = 100, offset: int = 0, processed: Optional[bool] = None):
    client = get_supabase()
    query = client.table("transactions").select("*").order("timestamp", desc=True).limit(limit).offset(offset)
    result = query.execute()
    return result.data


def get_unprocessed_transactions(limit: int = 50):
    """Get transactions that don't have risk assessments yet."""
    client = get_supabase()
    result = client.rpc("get_unprocessed_transactions", {"batch_limit": limit}).execute()
    return result.data


def get_risk_assessments(limit: int = 100, risk_level: Optional[str] = None):
    client = get_supabase()
    query = client.table("risk_assessments").select("*, transactions(*)").order("processed_at", desc=True).limit(limit)
    if risk_level:
        query = query.eq("risk_level", risk_level)
    result = query.execute()
    return result.data


def get_transactions_by_user(user_id: str, hours: int = 24):
    client = get_supabase()
    result = client.rpc("get_user_transactions_window", {
        "p_user_id": user_id,
        "p_hours": hours
    }).execute()
    return result.data


def get_transactions_by_card(card_last4: str, hours: int = 24):
    client = get_supabase()
    result = client.rpc("get_card_transactions_window", {
        "p_card_last4": card_last4,
        "p_hours": hours
    }).execute()
    return result.data


def get_transactions_by_device(device_id: str, hours: int = 24):
    client = get_supabase()
    result = client.rpc("get_device_transactions_window", {
        "p_device_id": device_id,
        "p_hours": hours
    }).execute()
    return result.data


def get_driver_passenger_pairs(days: int = 7):
    client = get_supabase()
    result = client.rpc("get_driver_passenger_pairs", {"p_days": days}).execute()
    return result.data


def get_dashboard_metrics():
    client = get_supabase()
    result = client.rpc("get_dashboard_metrics").execute()
    return result.data


def get_pipeline_state():
    client = get_supabase()
    result = client.table("pipeline_state").select("*").order("id", desc=True).limit(1).execute()
    return result.data[0] if result.data else None


def update_pipeline_state(status: str = None, transactions_processed: int = None):
    client = get_supabase()
    state = get_pipeline_state()
    update_data = {}
    if status:
        update_data["status"] = status
    if transactions_processed is not None:
        update_data["transactions_processed"] = transactions_processed
    update_data["updated_at"] = "now()"

    if state:
        client.table("pipeline_state").update(update_data).eq("id", state["id"]).execute()
    else:
        update_data["status"] = status or "stopped"
        update_data["transactions_processed"] = transactions_processed or 0
        client.table("pipeline_state").insert(update_data).execute()


def save_ml_model_metrics(model_name: str, model_type: str, precision: float, recall: float, f1: float, accuracy: float):
    client = get_supabase()
    client.table("ml_models").update({"is_active": False}).eq("is_active", True).execute()
    client.table("ml_models").insert({
        "model_name": model_name,
        "model_type": model_type,
        "precision_score": precision,
        "recall_score": recall,
        "f1_score": f1,
        "accuracy": accuracy,
        "is_active": True
    }).execute()


def get_ml_model_metrics():
    client = get_supabase()
    result = client.table("ml_models").select("*").eq("is_active", True).limit(1).execute()
    return result.data[0] if result.data else None

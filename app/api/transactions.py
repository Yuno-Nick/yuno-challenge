"""Transaction API endpoints."""
from fastapi import APIRouter, Query
from typing import Optional
from app.database import get_supabase, insert_transactions
from app.models.transaction import TransactionCreate, TransactionBatch

router = APIRouter()


@router.post("/")
def create_transaction(transaction: TransactionCreate):
    """Ingest a single transaction."""
    data = transaction.model_dump()
    data["timestamp"] = data["timestamp"].isoformat()
    result = insert_transactions([data])
    return {"status": "created", "data": result}


@router.post("/batch")
def create_batch(batch: TransactionBatch):
    """Ingest a batch of transactions."""
    data = [t.model_dump() for t in batch.transactions]
    for d in data:
        d["timestamp"] = d["timestamp"].isoformat()
    result = insert_transactions(data)
    return {"status": "created", "count": len(result)}


@router.get("/")
def list_transactions(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    risk_level: Optional[str] = None,
):
    """List transactions with optional filters."""
    client = get_supabase()

    # Get transactions
    txn_result = client.table("transactions").select(
        "transaction_id, timestamp, user_id, driver_id, card_last4, "
        "pickup_city, pickup_country, amount, currency"
    ).order("timestamp", desc=True).limit(limit).offset(offset).execute()

    # Get risk assessments for these transactions
    txn_ids = [t["transaction_id"] for t in txn_result.data]
    if txn_ids:
        risk_result = client.table("risk_assessments").select(
            "transaction_id, risk_score, risk_level"
        ).in_("transaction_id", txn_ids).execute()
        risk_map = {r["transaction_id"]: r for r in risk_result.data}
    else:
        risk_map = {}

    # Merge
    data = []
    for t in txn_result.data:
        risk = risk_map.get(t["transaction_id"], {})
        t["risk_assessments"] = [risk] if risk else []
        data.append(t)

    return {"data": data, "count": len(data)}


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str):
    """Get a single transaction with its risk assessment."""
    client = get_supabase()
    result = client.table("transactions").select(
        "*, risk_assessments(*)"
    ).eq("transaction_id", transaction_id).execute()

    if not result.data:
        return {"error": "Transaction not found"}
    return {"data": result.data[0]}

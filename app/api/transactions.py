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
    query = client.table("transactions").select(
        "*, risk_assessments(*)"
    ).order("timestamp", desc=True).limit(limit).offset(offset)

    if risk_level:
        query = query.eq("risk_assessments.risk_level", risk_level)

    result = query.execute()
    return {"data": result.data, "count": len(result.data)}


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

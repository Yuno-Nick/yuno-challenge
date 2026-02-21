"""Dashboard data API endpoints."""
from fastapi import APIRouter, Query
from app.database import get_supabase

router = APIRouter()


@router.get("/metrics")
def get_metrics():
    """Get current fraud dashboard metrics."""
    client = get_supabase()

    # Total transactions
    total_result = client.table("transactions").select("id", count="exact").execute()
    total_transactions = total_result.count or 0

    # Risk level counts
    risk_result = client.table("risk_assessments").select("risk_level, risk_score").execute()
    risk_data = risk_result.data or []

    high_risk = sum(1 for r in risk_data if r.get("risk_level") == "high_risk")
    medium_risk = sum(1 for r in risk_data if r.get("risk_level") == "medium_risk")
    low_risk = sum(1 for r in risk_data if r.get("risk_level") == "low_risk")
    processed = len(risk_data)

    fraud_rate = (high_risk / processed * 100) if processed > 0 else 0

    # Total amount at risk (from high-risk transactions)
    high_risk_txns = client.table("risk_assessments").select(
        "transaction_id, transactions(amount)"
    ).eq("risk_level", "high_risk").execute()

    amount_at_risk = sum(
        r.get("transactions", {}).get("amount", 0)
        for r in (high_risk_txns.data or [])
        if r.get("transactions")
    )

    avg_score = sum(r.get("risk_score", 0) for r in risk_data) / len(risk_data) if risk_data else 0

    return {
        "total_transactions": total_transactions,
        "processed_transactions": processed,
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "fraud_rate": round(fraud_rate, 2),
        "total_amount_at_risk": round(amount_at_risk, 2),
        "avg_risk_score": round(avg_score, 1),
    }


@router.get("/alerts")
def get_alerts(limit: int = Query(default=20, le=100)):
    """Get recent high-risk transaction alerts."""
    client = get_supabase()
    result = client.table("risk_assessments").select(
        "*, transactions(*)"
    ).eq("risk_level", "high_risk").order("processed_at", desc=True).limit(limit).execute()

    return {"data": result.data or []}


@router.get("/patterns")
def get_patterns():
    """Get aggregated pattern data for visualizations."""
    client = get_supabase()

    # All risk assessments with transaction data
    result = client.table("risk_assessments").select(
        "*, transactions(*)"
    ).execute()
    data = result.data or []

    # Fraud by country
    country_stats = {}
    for r in data:
        txn = r.get("transactions") or {}
        country = txn.get("pickup_country", "Unknown")
        if country not in country_stats:
            country_stats[country] = {"total": 0, "high_risk": 0}
        country_stats[country]["total"] += 1
        if r.get("risk_level") == "high_risk":
            country_stats[country]["high_risk"] += 1

    fraud_by_country = [
        {
            "country": k,
            "total": v["total"],
            "high_risk": v["high_risk"],
            "fraud_rate": round(v["high_risk"] / v["total"] * 100, 2) if v["total"] > 0 else 0
        }
        for k, v in country_stats.items()
    ]

    # Risk score distribution
    score_distribution = [r.get("risk_score", 0) for r in data]

    # Risk levels over time (by hour)
    time_series = {}
    for r in data:
        txn = r.get("transactions") or {}
        ts = txn.get("timestamp", "")[:13]  # YYYY-MM-DDTHH
        if ts:
            if ts not in time_series:
                time_series[ts] = {"timestamp": ts, "total": 0, "high_risk": 0, "medium_risk": 0}
            time_series[ts]["total"] += 1
            level = r.get("risk_level", "")
            if level in time_series[ts]:
                time_series[ts][level] += 1

    return {
        "fraud_by_country": fraud_by_country,
        "score_distribution": score_distribution,
        "time_series": sorted(time_series.values(), key=lambda x: x["timestamp"]),
    }

"""ML model API endpoints."""
from fastapi import APIRouter
import pandas as pd
from app.database import get_supabase, save_ml_model_metrics, get_ml_model_metrics
from app.scoring.ml_model import train_model, is_model_trained

router = APIRouter()


@router.post("/train")
def train_ml_model():
    """Train the ML model on current transaction data."""
    client = get_supabase()

    # Get all transactions with risk assessments
    txn_result = client.table("transactions").select("*").execute()
    risk_result = client.table("risk_assessments").select("*").execute()

    if not txn_result.data or not risk_result.data:
        return {"error": "Not enough data. Run the pipeline first."}

    transactions_df = pd.DataFrame(txn_result.data)
    indicators_df = pd.DataFrame(risk_result.data)

    if len(transactions_df) < 50:
        return {"error": f"Need at least 50 processed transactions. Currently have {len(transactions_df)}."}

    # Ensure is_fraudulent column exists
    if "is_fraudulent" not in transactions_df.columns:
        return {"error": "Transaction data missing is_fraudulent labels."}

    metrics = train_model(transactions_df, indicators_df)

    # Save metrics to DB
    save_ml_model_metrics(
        model_name="fraud_rf_v1",
        model_type="RandomForest",
        precision=metrics["precision"],
        recall=metrics["recall"],
        f1=metrics["f1"],
        accuracy=metrics["accuracy"],
    )

    return {
        "status": "trained",
        "metrics": {
            "precision": round(metrics["precision"], 4),
            "recall": round(metrics["recall"], 4),
            "f1": round(metrics["f1"], 4),
            "accuracy": round(metrics["accuracy"], 4),
            "roc_auc": round(metrics["roc_auc"], 4),
        },
        "confusion_matrix": metrics["confusion_matrix"],
        "feature_importance": metrics["feature_importance"],
        "roc_fpr": metrics["roc_fpr"],
        "roc_tpr": metrics["roc_tpr"],
    }


@router.get("/metrics")
def get_model_metrics():
    """Get current ML model performance metrics."""
    db_metrics = get_ml_model_metrics()
    if not db_metrics:
        return {"status": "no_model", "message": "No trained model found. POST /api/ml/train first."}

    return {
        "status": "active",
        "model": db_metrics,
    }


@router.get("/status")
def model_status():
    """Check if a trained model exists."""
    return {
        "trained": is_model_trained(),
        "db_metrics": get_ml_model_metrics(),
    }

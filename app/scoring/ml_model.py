"""ML-based risk scoring using Random Forest and Isolation Forest."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score, confusion_matrix, roc_curve, auc
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ml")
MODEL_PATH = os.path.join(MODEL_DIR, "trained_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")

_model = None
_scaler = None
_isolation_forest = None


def extract_features(transaction: dict, indicators: dict) -> dict:
    """Extract ML features from a transaction and its fraud indicators."""
    txn_time = transaction.get("timestamp")
    if isinstance(txn_time, str):
        try:
            txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))
        except ValueError:
            txn_time = datetime.now()

    return {
        "velocity_score": indicators.get("velocity_score", 0),
        "geographic_score": indicators.get("geographic_score", 0),
        "amount_score": indicators.get("amount_score", 0),
        "card_testing_score": indicators.get("card_testing_score", 0),
        "collusion_score": indicators.get("collusion_score", 0),
        "ato_score": indicators.get("ato_score", 0),
        "fraud_ring_score": indicators.get("fraud_ring_score", 0),
        "amount": transaction.get("amount", 0),
        "distance_km": transaction.get("distance_km", 0),
        "duration_minutes": transaction.get("duration_minutes", 0),
        "hour_of_day": txn_time.hour,
        "day_of_week": txn_time.weekday(),
    }


def train_model(transactions_df: pd.DataFrame, indicators_df: pd.DataFrame):
    """Train Random Forest + Isolation Forest on labeled data."""
    global _model, _scaler, _isolation_forest

    os.makedirs(MODEL_DIR, exist_ok=True)

    # Merge transactions with indicators
    merged = transactions_df.merge(indicators_df, on="transaction_id", how="inner")

    feature_cols = [
        "velocity_score", "geographic_score", "amount_score", "card_testing_score",
        "collusion_score", "ato_score", "fraud_ring_score",
        "amount", "distance_km", "duration_minutes"
    ]

    # Parse timestamps for time features
    merged["timestamp"] = pd.to_datetime(merged["timestamp"], format="ISO8601")
    merged["hour_of_day"] = merged["timestamp"].dt.hour
    merged["day_of_week"] = merged["timestamp"].dt.weekday
    feature_cols.extend(["hour_of_day", "day_of_week"])

    # Ensure all feature cols exist
    for col in feature_cols:
        if col not in merged.columns:
            merged[col] = 0

    X = merged[feature_cols].fillna(0).values
    y = merged["is_fraudulent"].astype(int).values

    # Scale features
    _scaler = StandardScaler()
    X_scaled = _scaler.fit_transform(X)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)

    # Train Random Forest
    _model = RandomForestClassifier(
        n_estimators=100, max_depth=10, random_state=42,
        class_weight="balanced"
    )
    _model.fit(X_train, y_train)

    # Train Isolation Forest (unsupervised anomaly detection)
    _isolation_forest = IsolationForest(n_estimators=100, contamination=0.15, random_state=42)
    _isolation_forest.fit(X_scaled)

    # Evaluate
    y_pred = _model.predict(X_test)
    y_prob = _model.predict_proba(X_test)[:, 1]

    metrics = {
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "feature_importance": dict(zip(feature_cols, _model.feature_importances_.tolist())),
    }

    # ROC curve
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    metrics["roc_auc"] = float(auc(fpr, tpr))
    metrics["roc_fpr"] = fpr.tolist()
    metrics["roc_tpr"] = tpr.tolist()

    # Save model
    joblib.dump(_model, MODEL_PATH)
    joblib.dump(_scaler, SCALER_PATH)

    return metrics


def predict_risk(features: dict) -> float:
    """Predict fraud probability for a single transaction. Returns score 0-100."""
    global _model, _scaler

    if _model is None:
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            _model = joblib.load(MODEL_PATH)
            _scaler = joblib.load(SCALER_PATH)
        else:
            return None

    feature_cols = [
        "velocity_score", "geographic_score", "amount_score", "card_testing_score",
        "collusion_score", "ato_score", "fraud_ring_score",
        "amount", "distance_km", "duration_minutes", "hour_of_day", "day_of_week"
    ]

    X = np.array([[features.get(col, 0) for col in feature_cols]])
    X_scaled = _scaler.transform(X)

    probability = _model.predict_proba(X_scaled)[0][1]
    return round(probability * 100, 1)


def is_model_trained() -> bool:
    """Check if a trained model exists."""
    return _model is not None or os.path.exists(MODEL_PATH)

"""ML Model Performance page."""
import streamlit as st
import httpx
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import pandas as pd
import numpy as np
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_api(endpoint: str):
    try:
        response = httpx.get(f"{API_URL}{endpoint}", timeout=10)
        return response.json()
    except Exception:
        return {"error": "API unavailable"}


def post_api(endpoint: str):
    try:
        response = httpx.post(f"{API_URL}{endpoint}", timeout=60)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


st.set_page_config(page_title="ML Performance", page_icon="🤖", layout="wide")
st.title("🤖 Machine Learning Model Performance")

# Train model button
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🎯 Train Model", use_container_width=True, type="primary"):
        with st.spinner("Training ML model... This may take a moment."):
            result = post_api("/api/ml/train")
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("Model trained successfully!")
                st.session_state["ml_result"] = result

with col2:
    model_status = get_api("/api/ml/status")
    if model_status.get("trained"):
        st.success("✅ Model is trained and active")
    else:
        st.warning("⚠️ No trained model. Click 'Train Model' after running the pipeline.")

st.divider()

# Check for training results in session state or API
ml_result = st.session_state.get("ml_result")
if not ml_result:
    # Try to get from API
    api_metrics = get_api("/api/ml/metrics")
    if api_metrics.get("status") == "active":
        ml_result = {"metrics": api_metrics.get("model", {})}

if ml_result and "metrics" in ml_result:
    metrics = ml_result["metrics"]

    # Performance metrics cards
    st.subheader("📊 Model Performance Metrics")
    c1, c2, c3, c4 = st.columns(4)

    precision = metrics.get("precision_score", metrics.get("precision", 0))
    recall = metrics.get("recall_score", metrics.get("recall", 0))
    f1 = metrics.get("f1_score", metrics.get("f1", 0))
    accuracy = metrics.get("accuracy", 0)

    with c1:
        st.metric("Precision", f"{precision:.4f}")
        st.caption("How many flagged transactions were actually fraudulent")
    with c2:
        st.metric("Recall", f"{recall:.4f}")
        st.caption("How many actual fraud cases were caught")
    with c3:
        st.metric("F1 Score", f"{f1:.4f}")
        st.caption("Harmonic mean of precision and recall")
    with c4:
        st.metric("Accuracy", f"{accuracy:.4f}")
        st.caption("Overall classification accuracy")

    st.divider()

    col1, col2 = st.columns(2)

    # Confusion Matrix
    with col1:
        st.subheader("🔢 Confusion Matrix")
        cm = ml_result.get("confusion_matrix")
        if cm:
            cm_array = np.array(cm)
            labels = ["Legitimate", "Fraudulent"]
            fig = px.imshow(
                cm_array,
                labels=dict(x="Predicted", y="Actual", color="Count"),
                x=labels,
                y=labels,
                color_continuous_scale="Blues",
                text_auto=True,
                title="Confusion Matrix",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    # ROC Curve
    with col2:
        st.subheader("📈 ROC Curve")
        roc_fpr = ml_result.get("roc_fpr")
        roc_tpr = ml_result.get("roc_tpr")
        roc_auc = metrics.get("roc_auc", 0)

        if roc_fpr and roc_tpr:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=roc_fpr, y=roc_tpr,
                mode="lines",
                name=f"ROC (AUC={roc_auc:.3f})",
                line=dict(color="blue", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1],
                mode="lines",
                name="Random",
                line=dict(color="gray", dash="dash"),
            ))
            fig.update_layout(
                title=f"ROC Curve (AUC = {roc_auc:.4f})",
                xaxis_title="False Positive Rate",
                yaxis_title="True Positive Rate",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ROC curve data not available. Retrain the model.")

    st.divider()

    # Feature Importance
    st.subheader("🎯 Feature Importance")
    feature_importance = ml_result.get("feature_importance")
    if feature_importance:
        fi_df = pd.DataFrame([
            {"Feature": k.replace("_", " ").title(), "Importance": v}
            for k, v in feature_importance.items()
        ]).sort_values("Importance", ascending=True)

        fig = px.bar(
            fi_df,
            x="Importance",
            y="Feature",
            orientation="h",
            title="Feature Importance (Random Forest)",
            color="Importance",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info(
        "No ML model has been trained yet. "
        "Run the pipeline to process transactions first, then click 'Train Model' above."
    )
    st.markdown("""
    ### How ML Scoring Works

    1. **Data Collection**: The pipeline processes transactions using rule-based fraud indicators
    2. **Feature Engineering**: Indicator scores + transaction features are used as ML features
    3. **Model Training**: A Random Forest classifier learns to predict fraud from labeled data
    4. **Hybrid Scoring**: Final risk score = 40% rule-based + 60% ML prediction
    5. **Continuous Improvement**: Retrain as more data is processed

    **ML Features used:**
    - Velocity score, Geographic score, Amount score, Card testing score
    - Collusion score, ATO score, Fraud ring score
    - Transaction amount, distance, duration
    - Hour of day, day of week
    """)

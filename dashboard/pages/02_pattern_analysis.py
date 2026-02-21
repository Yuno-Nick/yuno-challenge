"""Fraud pattern analysis and visualizations."""
import streamlit as st
import httpx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_api(endpoint: str):
    try:
        response = httpx.get(f"{API_URL}{endpoint}", timeout=10)
        return response.json()
    except Exception:
        return {"error": "API unavailable"}


st.set_page_config(page_title="Pattern Analysis", page_icon="📊", layout="wide")
st.title("📊 Fraud Pattern Analysis")

# Get pattern data
patterns = get_api("/api/dashboard/patterns")
if "error" in patterns:
    st.error("Could not load pattern data. Ensure the API is running and pipeline has processed data.")
    st.stop()

# === Chart 1: Fraud Rate by Country ===
st.subheader("🌍 Fraud Rate by Country")
fraud_by_country = patterns.get("fraud_by_country", [])
if fraud_by_country:
    df_country = pd.DataFrame(fraud_by_country)
    fig = px.bar(
        df_country,
        x="country",
        y="fraud_rate",
        color="fraud_rate",
        color_continuous_scale="Reds",
        text="fraud_rate",
        title="Fraud Rate by Country (%)",
        labels={"fraud_rate": "Fraud Rate (%)", "country": "Country"},
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Country detail table
    df_country["fraud_rate_fmt"] = df_country["fraud_rate"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(df_country[["country", "total", "high_risk", "fraud_rate_fmt"]].rename(columns={
        "country": "Country", "total": "Total Txns", "high_risk": "High Risk", "fraud_rate_fmt": "Fraud Rate"
    }), use_container_width=True, hide_index=True)
else:
    st.info("No country data yet.")

st.divider()

# === Chart 2: Risk Score Distribution ===
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Risk Score Distribution")
    scores = patterns.get("score_distribution", [])
    if scores:
        fig = px.histogram(
            x=scores,
            nbins=20,
            title="Distribution of Risk Scores",
            labels={"x": "Risk Score", "y": "Count"},
            color_discrete_sequence=["#FF6B6B"],
        )
        fig.add_vline(x=30, line_dash="dash", line_color="orange", annotation_text="Medium threshold")
        fig.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="High threshold")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No score data yet.")

with col2:
    st.subheader("🥧 Risk Level Distribution")
    metrics = get_api("/api/dashboard/metrics")
    if "error" not in metrics:
        risk_data = {
            "Risk Level": ["High Risk", "Medium Risk", "Low Risk"],
            "Count": [
                metrics.get("high_risk_count", 0),
                metrics.get("medium_risk_count", 0),
                metrics.get("low_risk_count", 0),
            ],
        }
        df_risk = pd.DataFrame(risk_data)
        if df_risk["Count"].sum() > 0:
            fig = px.pie(
                df_risk,
                values="Count",
                names="Risk Level",
                color="Risk Level",
                color_discrete_map={
                    "High Risk": "#FF4444",
                    "Medium Risk": "#FFB347",
                    "Low Risk": "#77DD77",
                },
                title="Risk Level Distribution",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# === Chart 3: Transaction Volume & Fraud Over Time ===
st.subheader("📉 Transaction Volume & Fraud Over Time")
time_series = patterns.get("time_series", [])
if time_series:
    df_time = pd.DataFrame(time_series)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_time["timestamp"], y=df_time["total"],
        mode="lines+markers", name="Total Transactions", line=dict(color="blue")
    ))
    fig.add_trace(go.Scatter(
        x=df_time["timestamp"], y=df_time["high_risk"],
        mode="lines+markers", name="High Risk", line=dict(color="red", dash="dash")
    ))
    fig.add_trace(go.Scatter(
        x=df_time["timestamp"], y=df_time["medium_risk"],
        mode="lines+markers", name="Medium Risk", line=dict(color="orange", dash="dot")
    ))
    fig.update_layout(
        title="Transaction Volume and Risk Levels Over Time",
        xaxis_title="Time",
        yaxis_title="Count",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No time series data yet.")

st.divider()

# === Chart 4: Amount Distribution by Risk Level ===
st.subheader("💰 Amount Distribution: High-Risk vs Low-Risk")
txn_data = get_api("/api/transactions?limit=500")
transactions = txn_data.get("data", [])
if transactions:
    rows = []
    for t in transactions:
        risk = (t.get("risk_assessments") or [{}])[0] if t.get("risk_assessments") else {}
        risk_level = risk.get("risk_level", "unknown")
        if risk_level != "unknown":
            rows.append({
                "amount": t.get("amount", 0),
                "risk_level": risk_level.replace("_", " ").title(),
                "currency": t.get("currency", ""),
                "country": t.get("pickup_country", ""),
            })

    if rows:
        df_amounts = pd.DataFrame(rows)
        fig = px.box(
            df_amounts,
            x="risk_level",
            y="amount",
            color="risk_level",
            color_discrete_map={
                "High Risk": "#FF4444",
                "Medium Risk": "#FFB347",
                "Low Risk": "#77DD77",
            },
            title="Transaction Amount Distribution by Risk Level",
            labels={"amount": "Amount", "risk_level": "Risk Level"},
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# === Chart 5: Geographic Heatmap ===
st.subheader("🗺️ Geographic Heatmap of Suspicious Transactions")
if transactions:
    high_risk_txns = []
    for t in transactions:
        risk = (t.get("risk_assessments") or [{}])[0] if t.get("risk_assessments") else {}
        if risk.get("risk_level") == "high_risk":
            high_risk_txns.append({
                "lat": t.get("pickup_lat", 0),
                "lon": t.get("pickup_lng", 0),
                "city": t.get("pickup_city", ""),
                "amount": t.get("amount", 0),
                "risk_score": risk.get("risk_score", 0),
            })

    if high_risk_txns:
        df_map = pd.DataFrame(high_risk_txns)
        fig = px.scatter_mapbox(
            df_map,
            lat="lat",
            lon="lon",
            size="risk_score",
            color="risk_score",
            color_continuous_scale="Reds",
            hover_data=["city", "amount", "risk_score"],
            title="High-Risk Transaction Locations",
            zoom=3,
            center={"lat": 0, "lon": 25},
        )
        fig.update_layout(
            mapbox_style="carto-positron",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No high-risk transactions to map yet.")

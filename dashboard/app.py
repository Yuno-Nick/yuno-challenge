"""Oasis Rides Fraud Detection Dashboard - Main App."""
import streamlit as st
import httpx
import os

st.set_page_config(
    page_title="Oasis Rides - Fraud Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_api(endpoint: str):
    """Helper to call the FastAPI backend."""
    try:
        response = httpx.get(f"{API_URL}{endpoint}", timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def post_api(endpoint: str):
    """Helper to POST to the FastAPI backend."""
    try:
        response = httpx.post(f"{API_URL}{endpoint}", timeout=30)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# Sidebar
st.sidebar.title("🛡️ Oasis Rides")
st.sidebar.markdown("**Fraud Intelligence Platform**")
st.sidebar.divider()

# Pipeline Controls
st.sidebar.subheader("Pipeline Controls")
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("▶ Start", use_container_width=True):
        result = post_api("/api/pipeline/start")
        st.sidebar.success(result.get("message", "Started"))

with col2:
    if st.button("⏹ Stop", use_container_width=True):
        result = post_api("/api/pipeline/stop")
        st.sidebar.info("Pipeline stopped")

# Pipeline Status
status = get_api("/api/pipeline/status")
if "error" not in status:
    status_emoji = {"running": "🟢", "stopped": "🔴", "completed": "✅"}.get(status.get("status"), "⚪")
    st.sidebar.markdown(f"**Status**: {status_emoji} {status.get('status', 'unknown')}")
    st.sidebar.progress(status.get("progress", 0) / 100)
    st.sidebar.caption(f"Processed: {status.get('processed', 0)} / {status.get('total', 0)}")

st.sidebar.divider()

if st.sidebar.button("🔄 Reset Pipeline", use_container_width=True):
    result = post_api("/api/pipeline/reset")
    st.sidebar.warning("Pipeline reset")

st.sidebar.divider()
st.sidebar.caption("Built for Yuno Challenge")

# Main content
st.title("🛡️ Oasis Rides Fraud Intelligence")
st.markdown("Real-time fraud detection pipeline for ride-hailing transactions across Nigeria, Kenya, and South Africa")

# KPI Metrics
metrics = get_api("/api/dashboard/metrics")
if "error" not in metrics:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Transactions",
            f"{metrics.get('total_transactions', 0):,}",
            delta=f"{metrics.get('processed_transactions', 0)} processed"
        )

    with col2:
        fraud_rate = metrics.get("fraud_rate", 0)
        st.metric(
            "Fraud Rate",
            f"{fraud_rate:.1f}%",
            delta=f"{metrics.get('high_risk_count', 0)} high-risk",
            delta_color="inverse"
        )

    with col3:
        st.metric(
            "Amount at Risk",
            f"${metrics.get('total_amount_at_risk', 0):,.0f}",
            delta_color="inverse"
        )

    with col4:
        st.metric(
            "Avg Risk Score",
            f"{metrics.get('avg_risk_score', 0):.1f}/100",
        )

    # Risk breakdown bar
    total_processed = metrics.get("processed_transactions", 0)
    if total_processed > 0:
        high = metrics.get("high_risk_count", 0)
        med = metrics.get("medium_risk_count", 0)
        low = metrics.get("low_risk_count", 0)

        st.markdown("#### Risk Level Breakdown")
        cols = st.columns([high or 1, med or 1, low or 1])
        with cols[0]:
            st.markdown(f"🔴 **High Risk**: {high} ({high/total_processed*100:.1f}%)")
        with cols[1]:
            st.markdown(f"🟡 **Medium Risk**: {med} ({med/total_processed*100:.1f}%)")
        with cols[2]:
            st.markdown(f"🟢 **Low Risk**: {low} ({low/total_processed*100:.1f}%)")

st.divider()
st.info("👈 Use the sidebar to navigate between dashboard pages. Start the pipeline to begin processing transactions.")

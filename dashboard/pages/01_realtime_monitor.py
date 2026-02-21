"""Real-time fraud monitoring page."""
import streamlit as st
import httpx
import pandas as pd
import os
import json

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_api(endpoint: str):
    try:
        response = httpx.get(f"{API_URL}{endpoint}", timeout=10)
        return response.json()
    except Exception:
        return {"error": "API unavailable"}


st.set_page_config(page_title="Real-Time Monitor", page_icon="📡", layout="wide")

# Auto-refresh every 5 seconds
if HAS_AUTOREFRESH:
    st_autorefresh(interval=5000, key="realtime_refresh")

st.title("📡 Real-Time Fraud Monitor")

# Pipeline status
status = get_api("/api/pipeline/status")
if "error" not in status:
    cols = st.columns([3, 1])
    with cols[0]:
        st.progress(status.get("progress", 0) / 100)
    with cols[1]:
        st.caption(f"{status.get('status', 'unknown')} | {status.get('processed', 0)}/{status.get('total', 0)}")

# KPIs
metrics = get_api("/api/dashboard/metrics")
if "error" not in metrics:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Processed", f"{metrics.get('processed_transactions', 0):,}")
    with c2:
        st.metric("High Risk", metrics.get("high_risk_count", 0))
    with c3:
        st.metric("Fraud Rate", f"{metrics.get('fraud_rate', 0):.1f}%")
    with c4:
        st.metric("Amount at Risk", f"${metrics.get('total_amount_at_risk', 0):,.0f}")

st.divider()

# High-Risk Alerts
st.subheader("🚨 High-Risk Transaction Alerts")
alerts = get_api("/api/dashboard/alerts?limit=20")
alert_data = alerts.get("data", [])

if alert_data:
    for alert in alert_data[:10]:
        txn = alert.get("transactions") or {}
        risk_score = alert.get("risk_score", 0)

        # Color based on score
        if risk_score >= 80:
            color = "🔴"
        elif risk_score >= 60:
            color = "🟠"
        else:
            color = "🟡"

        with st.expander(
            f"{color} Score: {risk_score}/100 | {txn.get('user_id', 'N/A')} | "
            f"****{txn.get('card_last4', '????')} | {txn.get('pickup_city', 'N/A')} | "
            f"{txn.get('amount', 0):.0f} {txn.get('currency', '')}"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Transaction ID**: `{alert.get('transaction_id', 'N/A')}`")
                st.markdown(f"**User**: {txn.get('user_id', 'N/A')}")
                st.markdown(f"**Driver**: {txn.get('driver_id', 'N/A')}")
                st.markdown(f"**Card**: ****{txn.get('card_last4', '????')}")
                st.markdown(f"**Device**: {txn.get('device_id', 'N/A')[:16]}...")
            with col2:
                st.markdown(f"**Amount**: {txn.get('amount', 0):.2f} {txn.get('currency', '')}")
                st.markdown(f"**Location**: {txn.get('pickup_city', 'N/A')}, {txn.get('pickup_country', 'N/A')}")
                st.markdown(f"**Distance**: {txn.get('distance_km', 0):.1f} km")
                st.markdown(f"**Time**: {txn.get('timestamp', 'N/A')}")

            # Indicator scores
            st.markdown("**Indicator Scores:**")
            indicators = {
                "Velocity": alert.get("velocity_score", 0),
                "Geographic": alert.get("geographic_score", 0),
                "Amount": alert.get("amount_score", 0),
                "Card Testing": alert.get("card_testing_score", 0),
                "Collusion": alert.get("collusion_score", 0),
                "Account Takeover": alert.get("ato_score", 0),
                "Fraud Ring": alert.get("fraud_ring_score", 0),
            }

            ind_cols = st.columns(len(indicators))
            for col, (name, score) in zip(ind_cols, indicators.items()):
                with col:
                    st.metric(name, f"{score:.0f}")

            # Triggered rules
            rules = alert.get("triggered_rules", [])
            if isinstance(rules, str):
                try:
                    rules = json.loads(rules)
                except (json.JSONDecodeError, TypeError):
                    rules = [rules]
            if rules:
                st.markdown("**Triggered Rules:**")
                for rule in rules:
                    st.code(rule)
else:
    st.info("No high-risk alerts yet. Start the pipeline to process transactions.")

st.divider()

# Recent transactions table
st.subheader("📋 Recent Transactions")
txn_data = get_api("/api/transactions?limit=50")
transactions = txn_data.get("data", [])

if transactions:
    rows = []
    for t in transactions:
        risk = (t.get("risk_assessments") or [{}])[0] if t.get("risk_assessments") else {}
        risk_level = risk.get("risk_level", "pending")
        risk_emoji = {"high_risk": "🔴", "medium_risk": "🟡", "low_risk": "🟢"}.get(risk_level, "⚪")

        rows.append({
            "Risk": f"{risk_emoji} {risk.get('risk_score', '-')}",
            "User": t.get("user_id", ""),
            "Card": f"****{t.get('card_last4', '')}",
            "Amount": f"{t.get('amount', 0):.0f} {t.get('currency', '')}",
            "City": t.get("pickup_city", ""),
            "Country": t.get("pickup_country", ""),
            "Time": str(t.get("timestamp", ""))[:19],
            "Level": risk_level,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No transactions yet. Start the pipeline.")

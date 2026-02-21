"""Advanced fraud detection page: collusion, ATO, fraud rings."""
import streamlit as st
import httpx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import os
from collections import defaultdict

API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_api(endpoint: str):
    try:
        response = httpx.get(f"{API_URL}{endpoint}", timeout=10)
        return response.json()
    except Exception:
        return {"error": "API unavailable"}


st.set_page_config(page_title="Advanced Detection", page_icon="🔍", layout="wide")
st.title("🔍 Advanced Fraud Pattern Detection")

# Get all high-risk alerts with details
alerts = get_api("/api/dashboard/alerts?limit=100")
alert_data = alerts.get("data", [])

# Also get all transactions for analysis
txn_data = get_api("/api/transactions?limit=500")
all_transactions = txn_data.get("data", [])

# ==============================
# 1. COLLUSION DETECTION
# ==============================
st.subheader("🤝 Collusion Detection")
st.markdown("Identifies suspicious driver-passenger pairs with unusually high ride frequency")

# Find collusion patterns from alerts
collusion_alerts = []
driver_passenger_pairs = defaultdict(lambda: {"count": 0, "total_amount": 0, "transactions": []})

for t in all_transactions:
    user_id = t.get("user_id", "")
    driver_id = t.get("driver_id", "")
    pair_key = f"{user_id} ↔ {driver_id}"
    driver_passenger_pairs[pair_key]["count"] += 1
    driver_passenger_pairs[pair_key]["total_amount"] += t.get("amount", 0)
    driver_passenger_pairs[pair_key]["user_id"] = user_id
    driver_passenger_pairs[pair_key]["driver_id"] = driver_id
    driver_passenger_pairs[pair_key]["city"] = t.get("pickup_city", "")
    driver_passenger_pairs[pair_key]["currency"] = t.get("currency", "")

# Filter suspicious pairs (5+ rides)
suspicious_pairs = [
    {
        "Pair": k,
        "Rides": v["count"],
        "Total Amount": f"{v['total_amount']:.0f} {v['currency']}",
        "User": v["user_id"],
        "Driver": v["driver_id"],
        "City": v["city"],
        "Risk": "🔴 High" if v["count"] >= 8 else "🟡 Moderate",
    }
    for k, v in driver_passenger_pairs.items()
    if v["count"] >= 5
]

if suspicious_pairs:
    df_pairs = pd.DataFrame(suspicious_pairs).sort_values("Rides", ascending=False)
    st.dataframe(df_pairs, use_container_width=True, hide_index=True)

    # Visualization
    fig = px.bar(
        df_pairs,
        x="Pair",
        y="Rides",
        color="Rides",
        color_continuous_scale="Reds",
        title="Suspicious Driver-Passenger Pairs (5+ rides)",
    )
    fig.add_hline(y=8, line_dash="dash", line_color="red", annotation_text="High-risk threshold")
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No collusion patterns detected yet.")

st.divider()

# ==============================
# 2. ACCOUNT TAKEOVER
# ==============================
st.subheader("🔓 Account Takeover Signals")
st.markdown("Flags sudden changes in user behavior: new payment method + unusual location")

ato_alerts = []
for alert in alert_data:
    rules = alert.get("triggered_rules", [])
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except (json.JSONDecodeError, TypeError):
            rules = [rules]

    for rule in rules:
        if isinstance(rule, str) and "ATO" in rule:
            txn = alert.get("transactions") or {}
            ato_alerts.append({
                "User": txn.get("user_id", ""),
                "New Card": f"****{txn.get('card_last4', '')}",
                "Location": f"{txn.get('pickup_city', '')}, {txn.get('pickup_country', '')}",
                "Amount": f"{txn.get('amount', 0):.0f} {txn.get('currency', '')}",
                "Score": alert.get("ato_score", 0),
                "Signal": rule,
                "Time": str(txn.get("timestamp", ""))[:19],
            })
            break

if ato_alerts:
    df_ato = pd.DataFrame(ato_alerts).sort_values("Score", ascending=False)
    st.dataframe(df_ato, use_container_width=True, hide_index=True)

    # Timeline
    if len(df_ato) > 1:
        fig = px.scatter(
            df_ato,
            x="Time",
            y="Score",
            color="User",
            size="Score",
            hover_data=["Signal", "Location", "New Card"],
            title="Account Takeover Signals Timeline",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No account takeover signals detected yet.")

st.divider()

# ==============================
# 3. FRAUD RING DETECTION
# ==============================
st.subheader("🕸️ Fraud Ring Detection")
st.markdown("Identifies groups of users/cards/devices sharing suspicious characteristics")

# Find shared devices
device_users = defaultdict(set)
device_txns = defaultdict(list)
for t in all_transactions:
    device = t.get("device_id", "")
    user = t.get("user_id", "")
    if device:
        device_users[device].add(user)
        device_txns[device].append(t)

# Filter devices shared by 2+ users
shared_devices = {
    device: users for device, users in device_users.items()
    if len(users) >= 2
}

if shared_devices:
    ring_data = []
    for device, users in shared_devices.items():
        txns = device_txns[device]
        amounts = [t.get("amount", 0) for t in txns]
        avg_amount = sum(amounts) / len(amounts) if amounts else 0

        ring_data.append({
            "Device": f"{device[:20]}...",
            "Users": len(users),
            "User IDs": ", ".join(sorted(users)[:5]),
            "Transactions": len(txns),
            "Avg Amount": f"{avg_amount:.0f}",
            "Risk": "🔴 High" if len(users) >= 3 else "🟡 Moderate",
        })

    df_rings = pd.DataFrame(ring_data).sort_values("Users", ascending=False)
    st.dataframe(df_rings, use_container_width=True, hide_index=True)

    # Network graph visualization
    if len(shared_devices) > 0:
        # Build network edges
        edges_x, edges_y = [], []
        node_x, node_y = [], []
        node_text = []
        node_color = []

        i = 0
        for device, users in list(shared_devices.items())[:10]:
            device_x, device_y = i * 3, 0
            node_x.append(device_x)
            node_y.append(device_y)
            node_text.append(f"Device: {device[:12]}...")
            node_color.append("red")

            for j, user in enumerate(users):
                user_x = device_x + (j - len(users) / 2) * 1.5
                user_y = 2
                node_x.append(user_x)
                node_y.append(user_y)
                node_text.append(f"User: {user}")
                node_color.append("blue" if len(users) >= 3 else "orange")

                edges_x.extend([device_x, user_x, None])
                edges_y.extend([device_y, user_y, None])

            i += 1

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=edges_x, y=edges_y, mode="lines",
            line=dict(color="gray", width=1), hoverinfo="none"
        ))
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            marker=dict(size=20, color=node_color),
            text=node_text, textposition="top center",
            hoverinfo="text",
        ))
        fig.update_layout(
            title="Device-User Network (Shared Devices)",
            showlegend=False,
            height=500,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No fraud ring patterns detected yet.")

# Fraud ring alerts from triggered rules
ring_alerts = []
for alert in alert_data:
    rules = alert.get("triggered_rules", [])
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except (json.JSONDecodeError, TypeError):
            rules = [rules]

    for rule in rules:
        if isinstance(rule, str) and "FRAUD_RING" in rule:
            txn = alert.get("transactions") or {}
            ring_alerts.append({
                "User": txn.get("user_id", ""),
                "Device": txn.get("device_id", "")[:16] + "...",
                "Score": alert.get("fraud_ring_score", 0),
                "Signal": rule,
            })
            break

if ring_alerts:
    st.markdown("#### Fraud Ring Alerts from Pipeline")
    df_ring_alerts = pd.DataFrame(ring_alerts)
    st.dataframe(df_ring_alerts, use_container_width=True, hide_index=True)

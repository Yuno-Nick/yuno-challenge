"""Fraud ring detection: identify groups sharing devices/patterns."""
from datetime import datetime, timedelta
from collections import defaultdict


def calculate_fraud_ring_score(transaction: dict, all_transactions: list[dict]) -> tuple[float, list[str]]:
    """
    Detect fraud rings by analyzing device sharing and transaction pattern similarity.
    Returns (score 0-100, list of triggered rules).
    """
    device_id = transaction.get("device_id")
    user_id = transaction.get("user_id")
    amount = transaction.get("amount", 0)
    txn_time = transaction.get("timestamp")

    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))

    triggered = []
    score = 0

    # Find all users who share this device
    device_users = set()
    device_txns = []
    window_start = txn_time - timedelta(days=7)

    for t in all_transactions:
        if t.get("device_id") == device_id:
            t_time = t.get("timestamp")
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time.replace("Z", "+00:00").replace("+00:00", ""))
                except ValueError:
                    continue
            if window_start <= t_time <= txn_time:
                device_users.add(t.get("user_id"))
                device_txns.append(t)

    num_users_sharing = len(device_users)

    if num_users_sharing >= 4:
        score = 90
        triggered.append(
            f"FRAUD_RING_HIGH: {num_users_sharing} users sharing device {device_id[:12]}..."
        )
    elif num_users_sharing >= 3:
        score = 70
        triggered.append(
            f"FRAUD_RING_MODERATE: {num_users_sharing} users sharing device {device_id[:12]}..."
        )
    elif num_users_sharing >= 2:
        # Only flag if there are other suspicious indicators
        score = 20
        triggered.append(
            f"FRAUD_RING_LOW: {num_users_sharing} users sharing device"
        )

    # Check for similar transaction amounts (within 20%)
    if num_users_sharing >= 3 and device_txns:
        amounts = [t.get("amount", 0) for t in device_txns]
        if amounts:
            avg_amount = sum(amounts) / len(amounts)
            if avg_amount > 0:
                similar_count = sum(1 for a in amounts if abs(a - avg_amount) / avg_amount < 0.2)
                similarity_ratio = similar_count / len(amounts)

                if similarity_ratio > 0.7:
                    score = min(score + 20, 100)
                    triggered.append(
                        f"FRAUD_RING_SIMILAR_AMOUNTS: {similarity_ratio:.0%} of transactions "
                        f"within 20% of avg={avg_amount:.0f}"
                    )

    # Check for concentrated time window
    if num_users_sharing >= 3 and device_txns:
        times = []
        for t in device_txns:
            t_time = t.get("timestamp")
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time.replace("Z", "+00:00").replace("+00:00", ""))
                    times.append(t_time)
                except ValueError:
                    continue

        if len(times) >= 3:
            times.sort()
            time_span_hours = (times[-1] - times[0]).total_seconds() / 3600
            if time_span_hours < 24 and len(times) >= 5:
                score = min(score + 15, 100)
                triggered.append(
                    f"FRAUD_RING_TIME_CLUSTER: {len(times)} transactions in {time_span_hours:.1f}h"
                )

    return score, triggered

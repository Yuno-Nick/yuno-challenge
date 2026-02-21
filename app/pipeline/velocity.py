"""Velocity check: detect unusually high transaction frequency."""
from datetime import datetime, timedelta
from app.config import settings


def calculate_velocity_score(transaction: dict, all_transactions: list[dict]) -> tuple[float, list[str]]:
    """
    Check how many transactions this user/card/device has made in recent time windows.
    Returns (score 0-100, list of triggered rules).
    """
    user_id = transaction.get("user_id")
    card_last4 = transaction.get("card_last4")
    device_id = transaction.get("device_id")
    txn_time = transaction.get("timestamp")

    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))

    triggered = []
    scores = []

    # Check by user_id
    user_1h = count_in_window(all_transactions, "user_id", user_id, txn_time, hours=1)
    user_24h = count_in_window(all_transactions, "user_id", user_id, txn_time, hours=24)

    # Check by card
    card_1h = count_in_window(all_transactions, "card_last4", card_last4, txn_time, hours=1)
    card_2h = count_in_window(all_transactions, "card_last4", card_last4, txn_time, hours=2)

    # Check by device
    device_1h = count_in_window(all_transactions, "device_id", device_id, txn_time, hours=1)

    max_1h = max(user_1h, card_1h, device_1h)
    max_2h = max(card_2h, user_1h)  # 2h window

    if max_1h >= 10:
        scores.append(100)
        triggered.append(f"VELOCITY_EXTREME: {max_1h} transactions in 1h")
    elif max_1h >= 8:
        scores.append(80)
        triggered.append(f"VELOCITY_VERY_HIGH: {max_1h} transactions in 1h")
    elif max_1h >= 6:
        scores.append(50)
        triggered.append(f"VELOCITY_HIGH: {max_1h} transactions in 1h")
    elif max_1h >= 3:
        scores.append(20)
        triggered.append(f"VELOCITY_MODERATE: {max_1h} transactions in 1h")

    if max_2h >= 10:
        scores.append(90)
        triggered.append(f"VELOCITY_2H_HIGH: {max_2h} transactions in 2h")

    if user_24h >= 15:
        scores.append(60)
        triggered.append(f"VELOCITY_24H_HIGH: {user_24h} transactions in 24h")

    final_score = max(scores) if scores else 0
    return min(final_score, 100), triggered


def count_in_window(transactions: list[dict], field: str, value: str,
                    current_time: datetime, hours: int) -> int:
    """Count transactions matching field=value within the time window."""
    window_start = current_time - timedelta(hours=hours)
    count = 0
    for txn in transactions:
        txn_time = txn.get("timestamp")
        if isinstance(txn_time, str):
            try:
                txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))
            except ValueError:
                continue

        if txn.get(field) == value and window_start <= txn_time <= current_time:
            count += 1
    return count

"""Geographic anomaly detection: identify impossible travel patterns."""
import math
from datetime import datetime, timedelta


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371  # Earth's radius in km
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    dlat = lat2 - lat1
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def calculate_geographic_score(transaction: dict, all_transactions: list[dict]) -> tuple[float, list[str]]:
    """
    Detect geographic anomalies by checking if user traveled impossibly fast.
    Returns (score 0-100, list of triggered rules).
    """
    user_id = transaction.get("user_id")
    txn_time = transaction.get("timestamp")
    txn_lat = transaction.get("pickup_lat")
    txn_lng = transaction.get("pickup_lng")
    txn_country = transaction.get("pickup_country")

    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))

    triggered = []
    max_score = 0

    # Find this user's previous transactions
    user_txns = []
    for t in all_transactions:
        if t.get("user_id") == user_id and t.get("transaction_id") != transaction.get("transaction_id"):
            t_time = t.get("timestamp")
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time.replace("Z", "+00:00").replace("+00:00", ""))
                except ValueError:
                    continue
            if t_time < txn_time:
                user_txns.append({**t, "_parsed_time": t_time})

    if not user_txns:
        return 0, []

    # Sort by time descending, check most recent
    user_txns.sort(key=lambda x: x["_parsed_time"], reverse=True)

    for prev in user_txns[:5]:  # Check last 5 transactions
        prev_lat = prev.get("pickup_lat")
        prev_lng = prev.get("pickup_lng")
        prev_time = prev["_parsed_time"]
        prev_country = prev.get("pickup_country")

        distance_km = haversine_km(prev_lat, prev_lng, txn_lat, txn_lng)
        time_diff_hours = (txn_time - prev_time).total_seconds() / 3600

        if time_diff_hours <= 0:
            continue

        speed_kmh = distance_km / time_diff_hours

        # Impossible travel (faster than commercial aircraft)
        if speed_kmh > 900 and distance_km > 100:
            max_score = max(max_score, 100)
            triggered.append(
                f"GEO_IMPOSSIBLE_TRAVEL: {distance_km:.0f}km in {time_diff_hours:.1f}h "
                f"({speed_kmh:.0f}km/h) from {prev.get('pickup_city')} to {transaction.get('pickup_city')}"
            )
        elif speed_kmh > 500 and distance_km > 100:
            max_score = max(max_score, 70)
            triggered.append(
                f"GEO_SUSPICIOUS_TRAVEL: {distance_km:.0f}km in {time_diff_hours:.1f}h ({speed_kmh:.0f}km/h)"
            )
        # Different country in short time
        elif prev_country != txn_country and time_diff_hours < 3:
            max_score = max(max_score, 80)
            triggered.append(
                f"GEO_COUNTRY_CHANGE: {prev_country} to {txn_country} in {time_diff_hours:.1f}h"
            )

    return min(max_score, 100), triggered

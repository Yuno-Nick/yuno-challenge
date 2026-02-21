"""Collusion detection: identify suspicious driver-passenger pairs."""
from datetime import datetime, timedelta
from app.pipeline.geographic import haversine_km


def calculate_collusion_score(transaction: dict, all_transactions: list[dict]) -> tuple[float, list[str]]:
    """
    Detect collusion between drivers and passengers.
    Returns (score 0-100, list of triggered rules).
    """
    user_id = transaction.get("user_id")
    driver_id = transaction.get("driver_id")
    txn_time = transaction.get("timestamp")
    pickup_lat = transaction.get("pickup_lat")
    pickup_lng = transaction.get("pickup_lng")
    dropoff_lat = transaction.get("dropoff_lat")
    dropoff_lng = transaction.get("dropoff_lng")

    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))

    triggered = []
    score = 0

    # Count rides between this driver-passenger pair in last 7 days
    pair_count = 0
    circular_count = 0
    window_start = txn_time - timedelta(days=7)

    for t in all_transactions:
        if t.get("user_id") == user_id and t.get("driver_id") == driver_id:
            t_time = t.get("timestamp")
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time.replace("Z", "+00:00").replace("+00:00", ""))
                except ValueError:
                    continue
            if window_start <= t_time <= txn_time:
                pair_count += 1
                # Check for circular route
                t_pickup_lat = t.get("pickup_lat", 0)
                t_pickup_lng = t.get("pickup_lng", 0)
                t_dropoff_lat = t.get("dropoff_lat", 0)
                t_dropoff_lng = t.get("dropoff_lng", 0)
                route_distance = haversine_km(t_pickup_lat, t_pickup_lng, t_dropoff_lat, t_dropoff_lng)
                if route_distance < 0.5:  # Dropoff within 500m of pickup
                    circular_count += 1

    if pair_count >= 8:
        score = 80
        triggered.append(
            f"COLLUSION_HIGH: {pair_count} rides between {user_id} and {driver_id} in 7 days"
        )
    elif pair_count >= 5:
        score = 40
        triggered.append(
            f"COLLUSION_MODERATE: {pair_count} rides between {user_id} and {driver_id} in 7 days"
        )

    # Circular route bonus
    if circular_count >= 3:
        score = min(score + 20, 100)
        triggered.append(
            f"COLLUSION_CIRCULAR: {circular_count} circular routes (pickup~=dropoff)"
        )

    # Check current transaction for circular route
    if pickup_lat and dropoff_lat:
        current_distance = haversine_km(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
        if current_distance < 0.5 and pair_count >= 3:
            score = min(score + 15, 100)
            triggered.append(f"COLLUSION_CIRCULAR_CURRENT: route distance only {current_distance:.2f}km")

    return score, triggered

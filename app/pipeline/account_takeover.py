"""Account takeover detection: new card + new location signals."""
from datetime import datetime, timedelta


def calculate_ato_score(transaction: dict, all_transactions: list[dict]) -> tuple[float, list[str]]:
    """
    Detect account takeover signals: new payment method + unusual location.
    Returns (score 0-100, list of triggered rules).
    """
    user_id = transaction.get("user_id")
    card_last4 = transaction.get("card_last4")
    device_id = transaction.get("device_id")
    pickup_country = transaction.get("pickup_country")
    pickup_city = transaction.get("pickup_city")
    txn_time = transaction.get("timestamp")

    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))

    triggered = []
    score = 0

    # Get user's historical data (last 30 days)
    window_start = txn_time - timedelta(days=30)
    user_history = []
    for t in all_transactions:
        if (t.get("user_id") == user_id and
                t.get("transaction_id") != transaction.get("transaction_id")):
            t_time = t.get("timestamp")
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time.replace("Z", "+00:00").replace("+00:00", ""))
                except ValueError:
                    continue
            if window_start <= t_time < txn_time:
                user_history.append({**t, "_parsed_time": t_time})

    if not user_history:
        return 0, []

    # Check if card is new for this user
    known_cards = set(t.get("card_last4") for t in user_history)
    is_new_card = card_last4 not in known_cards

    # Check if device is new
    known_devices = set(t.get("device_id") for t in user_history)
    is_new_device = device_id not in known_devices

    # Check if location is new
    known_countries = set(t.get("pickup_country") for t in user_history)
    known_cities = set(t.get("pickup_city") for t in user_history)
    is_new_country = pickup_country not in known_countries
    is_new_city = pickup_city not in known_cities

    # Scoring combinations
    if is_new_card and is_new_country:
        score = 85
        triggered.append(
            f"ATO_HIGH: New card ****{card_last4} + new country ({pickup_country})"
        )
    elif is_new_card and is_new_city:
        score = 65
        triggered.append(
            f"ATO_MODERATE: New card ****{card_last4} + new city ({pickup_city})"
        )
    elif is_new_card and is_new_device:
        score = 70
        triggered.append(
            f"ATO_NEW_CARD_DEVICE: New card ****{card_last4} + new device"
        )
    elif is_new_card:
        score = 30
        triggered.append(f"ATO_NEW_CARD: New card ****{card_last4} for user {user_id}")

    if is_new_device and is_new_country and not is_new_card:
        score = max(score, 50)
        triggered.append(
            f"ATO_NEW_DEVICE_COUNTRY: New device + new country ({pickup_country})"
        )

    # Check velocity after card change (multiple transactions right after new card)
    if is_new_card:
        recent_new_card_txns = sum(
            1 for t in all_transactions
            if t.get("user_id") == user_id and t.get("card_last4") == card_last4
        )
        if recent_new_card_txns >= 3:
            score = min(score + 15, 100)
            triggered.append(
                f"ATO_RAPID_USE: {recent_new_card_txns} transactions on new card quickly"
            )

    return score, triggered

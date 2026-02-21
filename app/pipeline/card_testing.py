"""Card testing pattern detection: small transactions followed by large ones."""
from datetime import datetime, timedelta


def calculate_card_testing_score(transaction: dict, all_transactions: list[dict]) -> tuple[float, list[str]]:
    """
    Detect card testing patterns: multiple small transactions followed by large ones.
    Returns (score 0-100, list of triggered rules).
    """
    card_last4 = transaction.get("card_last4")
    amount = transaction.get("amount", 0)
    currency = transaction.get("currency")
    txn_time = transaction.get("timestamp")

    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))

    triggered = []

    # Get card's recent transactions (last 24h)
    card_txns = []
    for t in all_transactions:
        if (t.get("card_last4") == card_last4 and
                t.get("transaction_id") != transaction.get("transaction_id")):
            t_time = t.get("timestamp")
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time.replace("Z", "+00:00").replace("+00:00", ""))
                except ValueError:
                    continue
            time_diff = (txn_time - t_time).total_seconds() / 3600
            if 0 < time_diff <= 24:
                card_txns.append({**t, "_parsed_time": t_time})

    if not card_txns:
        return 0, []

    # Define "small" threshold based on currency
    small_thresholds = {"NGN": 300, "KES": 150, "ZAR": 30}
    small_threshold = small_thresholds.get(currency, 300)

    # Count small transactions
    small_txns = [t for t in card_txns if t.get("amount", 0) < small_threshold]
    num_small = len(small_txns)

    # Pattern: multiple small transactions exist AND current is large
    if num_small >= 3:
        avg_small = sum(t.get("amount", 0) for t in small_txns) / num_small if num_small > 0 else 1

        if amount > avg_small * 10:
            # Classic card testing: small probes followed by large charge
            score = 95
            triggered.append(
                f"CARD_TESTING_CONFIRMED: {num_small} small txns (avg={avg_small:.0f}) "
                f"then large={amount} ({amount / avg_small:.0f}x multiplier)"
            )
        elif amount > avg_small * 5:
            score = 70
            triggered.append(
                f"CARD_TESTING_LIKELY: {num_small} small txns then medium-large={amount}"
            )
        else:
            # Just clustering of small transactions (probe phase)
            score = 50
            triggered.append(
                f"CARD_TESTING_PROBING: {num_small} small transactions from card ****{card_last4}"
            )
    elif num_small >= 2 and amount > small_threshold * 10:
        score = 40
        triggered.append(
            f"CARD_TESTING_POSSIBLE: {num_small} small txns before large={amount}"
        )
    else:
        score = 0

    return score, triggered

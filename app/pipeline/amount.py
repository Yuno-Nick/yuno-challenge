"""Amount anomaly detection: identify unusual transaction amounts."""
from datetime import datetime, timedelta
import math


def calculate_amount_score(transaction: dict, all_transactions: list[dict]) -> tuple[float, list[str]]:
    """
    Detect amount anomalies using z-score analysis.
    Returns (score 0-100, list of triggered rules).
    """
    user_id = transaction.get("user_id")
    amount = transaction.get("amount", 0)
    currency = transaction.get("currency")
    txn_time = transaction.get("timestamp")

    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00").replace("+00:00", ""))

    triggered = []

    # Get user's historical transactions (same currency)
    user_amounts = []
    for t in all_transactions:
        if (t.get("user_id") == user_id and
                t.get("currency") == currency and
                t.get("transaction_id") != transaction.get("transaction_id")):
            t_time = t.get("timestamp")
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time.replace("Z", "+00:00").replace("+00:00", ""))
                except ValueError:
                    continue
            if t_time < txn_time:
                user_amounts.append(t.get("amount", 0))

    if len(user_amounts) < 5:
        # Not enough personal history - only flag extreme outliers vs currency average
        currency_amounts = [t.get("amount", 0) for t in all_transactions
                           if t.get("currency") == currency]
        if len(currency_amounts) < 10:
            return 0, []
        user_amounts = currency_amounts
        # Require higher z-score when using population average (less confident)
        using_population = True
    else:
        using_population = False

    mean = sum(user_amounts) / len(user_amounts)
    variance = sum((x - mean) ** 2 for x in user_amounts) / len(user_amounts)
    std = math.sqrt(variance) if variance > 0 else 1

    z_score = (amount - mean) / std if std > 0 else 0

    # Higher thresholds when using population data to reduce false positives
    high_threshold = 4.0 if using_population else 3.0
    med_threshold = 3.0 if using_population else 2.0
    low_threshold = 2.5 if using_population else 1.5

    if z_score > high_threshold:
        score = 80
        triggered.append(f"AMOUNT_EXTREME: z-score={z_score:.1f}, amount={amount} vs avg={mean:.0f}")
    elif z_score > med_threshold:
        score = 50
        triggered.append(f"AMOUNT_HIGH: z-score={z_score:.1f}, amount={amount} vs avg={mean:.0f}")
    elif z_score > low_threshold:
        score = 30
        triggered.append(f"AMOUNT_ELEVATED: z-score={z_score:.1f}, amount={amount} vs avg={mean:.0f}")
    else:
        score = 0

    return score, triggered

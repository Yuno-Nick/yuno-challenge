"""Main pipeline orchestrator: processes transactions and calculates risk scores."""
import pandas as pd
from datetime import datetime
from typing import Optional

from app.pipeline.velocity import calculate_velocity_score
from app.pipeline.geographic import calculate_geographic_score
from app.pipeline.amount import calculate_amount_score
from app.pipeline.card_testing import calculate_card_testing_score
from app.pipeline.collusion import calculate_collusion_score
from app.pipeline.account_takeover import calculate_ato_score
from app.pipeline.fraud_ring import calculate_fraud_ring_score
from app.scoring.hybrid import calculate_hybrid_score


def process_single_transaction(transaction: dict, all_transactions: list[dict]) -> dict:
    """
    Process a single transaction through all fraud detection indicators.
    Returns a risk assessment dict.
    """
    # Calculate all fraud indicators
    velocity_score, velocity_rules = calculate_velocity_score(transaction, all_transactions)
    geographic_score, geo_rules = calculate_geographic_score(transaction, all_transactions)
    amount_score, amount_rules = calculate_amount_score(transaction, all_transactions)
    card_testing_score, ct_rules = calculate_card_testing_score(transaction, all_transactions)
    collusion_score, collusion_rules = calculate_collusion_score(transaction, all_transactions)
    ato_score, ato_rules = calculate_ato_score(transaction, all_transactions)
    fraud_ring_score, ring_rules = calculate_fraud_ring_score(transaction, all_transactions)

    indicators = {
        "velocity_score": velocity_score,
        "geographic_score": geographic_score,
        "amount_score": amount_score,
        "card_testing_score": card_testing_score,
        "collusion_score": collusion_score,
        "ato_score": ato_score,
        "fraud_ring_score": fraud_ring_score,
    }

    # Calculate hybrid score (rule-based + ML)
    final_score, risk_level, ml_score = calculate_hybrid_score(transaction, indicators)

    # Collect all triggered rules
    triggered_rules = (velocity_rules + geo_rules + amount_rules + ct_rules +
                       collusion_rules + ato_rules + ring_rules)

    return {
        "transaction_id": transaction["transaction_id"],
        "risk_score": final_score,
        "risk_level": risk_level,
        "velocity_score": velocity_score,
        "geographic_score": geographic_score,
        "amount_score": amount_score,
        "card_testing_score": card_testing_score,
        "collusion_score": collusion_score,
        "ato_score": ato_score,
        "fraud_ring_score": fraud_ring_score,
        "ml_score": ml_score,
        "triggered_rules": triggered_rules,
        "processed_at": datetime.utcnow().isoformat(),
    }


def process_batch(batch: list[dict], all_transactions: list[dict]) -> list[dict]:
    """Process a batch of transactions."""
    results = []
    # Build up context as we process
    running_context = list(all_transactions)

    for txn in batch:
        assessment = process_single_transaction(txn, running_context)
        results.append(assessment)
        running_context.append(txn)  # Add to context for next transaction

    return results


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Process an entire DataFrame of transactions. Returns DataFrame with risk assessments."""
    transactions = df.to_dict("records")
    all_assessments = []

    # Process in order of timestamp
    sorted_txns = sorted(transactions, key=lambda x: x.get("timestamp", ""))
    processed_so_far = []

    for txn in sorted_txns:
        assessment = process_single_transaction(txn, processed_so_far)
        all_assessments.append(assessment)
        processed_so_far.append(txn)

    return pd.DataFrame(all_assessments)

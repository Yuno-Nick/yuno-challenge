"""Unit tests for the fraud detection pipeline."""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipeline.velocity import calculate_velocity_score
from app.pipeline.geographic import calculate_geographic_score, haversine_km
from app.pipeline.amount import calculate_amount_score
from app.pipeline.card_testing import calculate_card_testing_score
from app.pipeline.collusion import calculate_collusion_score
from app.pipeline.account_takeover import calculate_ato_score
from app.pipeline.fraud_ring import calculate_fraud_ring_score
from app.scoring.rule_based import calculate_rule_based_score
from app.pipeline.processor import process_single_transaction, process_dataframe

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name} {detail}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} {detail}")


def test_haversine():
    print("[1/9] Haversine Distance")
    # Lagos to Nairobi ~3,800 km
    d = haversine_km(6.5244, 3.3792, -1.2921, 36.8219)
    test("Lagos-Nairobi distance", 3500 < d < 4100, f"-> {d:.0f} km")

    # Same point
    d = haversine_km(6.5244, 3.3792, 6.5244, 3.3792)
    test("Same point = 0", d < 0.01, f"-> {d:.4f} km")

    # Johannesburg to Cape Town ~1,260 km
    d = haversine_km(-26.2041, 28.0473, -33.9249, 18.4241)
    test("Joburg-CapeTown distance", 1100 < d < 1400, f"-> {d:.0f} km")


def test_velocity():
    print("\n[2/9] Velocity Detection")
    # High velocity: 12 transactions in 1 hour
    txn = {"user_id": "USR-001", "card_last4": "1234", "device_id": "DEV-001",
           "timestamp": "2025-02-15T12:00:00", "transaction_id": "TXN-TEST"}
    history = [
        {"user_id": "USR-001", "card_last4": "1234", "device_id": "DEV-001",
         "timestamp": f"2025-02-15T11:{50 + i}:00", "transaction_id": f"TXN-H{i}"}
        for i in range(12)
    ]
    score, rules = calculate_velocity_score(txn, history)
    test("High velocity score >= 80", score >= 80, f"-> score={score}")
    test("Has velocity rule", any("VELOCITY" in r for r in rules))

    # Normal: 1 transaction
    score2, rules2 = calculate_velocity_score(txn, [history[0]])
    test("Normal velocity score = 0", score2 == 0, f"-> score={score2}")


def test_geographic():
    print("\n[3/9] Geographic Anomaly Detection")
    # Impossible travel: Lagos to Nairobi in 15 min
    txn = {"user_id": "USR-GEO", "pickup_lat": -1.2921, "pickup_lng": 36.8219,
           "pickup_country": "Kenya", "pickup_city": "Nairobi",
           "timestamp": "2025-02-15T10:15:00", "transaction_id": "TXN-GEO2"}
    prev = [{"user_id": "USR-GEO", "pickup_lat": 6.5244, "pickup_lng": 3.3792,
             "pickup_country": "Nigeria", "pickup_city": "Lagos",
             "timestamp": "2025-02-15T10:00:00", "transaction_id": "TXN-GEO1"}]

    score, rules = calculate_geographic_score(txn, prev)
    test("Impossible travel score = 100", score == 100, f"-> score={score}")
    test("Has geo rule", any("GEO_IMPOSSIBLE" in r for r in rules))

    # Normal: same city
    txn_normal = {"user_id": "USR-N", "pickup_lat": 6.53, "pickup_lng": 3.38,
                  "pickup_country": "Nigeria", "pickup_city": "Lagos",
                  "timestamp": "2025-02-15T12:00:00", "transaction_id": "TXN-N2"}
    prev_normal = [{"user_id": "USR-N", "pickup_lat": 6.52, "pickup_lng": 3.37,
                    "pickup_country": "Nigeria", "pickup_city": "Lagos",
                    "timestamp": "2025-02-15T11:00:00", "transaction_id": "TXN-N1"}]
    score2, _ = calculate_geographic_score(txn_normal, prev_normal)
    test("Same city score = 0", score2 == 0, f"-> score={score2}")


def test_amount():
    print("\n[4/9] Amount Anomaly Detection")
    # Build history with consistent amounts around 1000 NGN
    history = [
        {"user_id": "USR-AMT", "currency": "NGN", "amount": 900 + i * 20,
         "timestamp": f"2025-02-{10 + i}T10:00:00", "transaction_id": f"TXN-A{i}"}
        for i in range(10)
    ]
    # Extreme amount
    txn = {"user_id": "USR-AMT", "currency": "NGN", "amount": 15000,
           "timestamp": "2025-02-21T10:00:00", "transaction_id": "TXN-ABIG"}
    score, rules = calculate_amount_score(txn, history)
    test("Extreme amount score >= 50", score >= 50, f"-> score={score}")

    # Normal amount
    txn_normal = {"user_id": "USR-AMT", "currency": "NGN", "amount": 1050,
                  "timestamp": "2025-02-21T10:00:00", "transaction_id": "TXN-ANORM"}
    score2, _ = calculate_amount_score(txn_normal, history)
    test("Normal amount score = 0", score2 == 0, f"-> score={score2}")


def test_card_testing():
    print("\n[5/9] Card Testing Detection")
    # 4 small transactions then 1 large
    history = [
        {"card_last4": "9999", "currency": "NGN", "amount": 100 + i * 10,
         "timestamp": f"2025-02-15T10:{10 + i * 5}:00", "transaction_id": f"TXN-CT{i}"}
        for i in range(4)
    ]
    txn_large = {"card_last4": "9999", "currency": "NGN", "amount": 12000,
                 "timestamp": "2025-02-15T12:00:00", "transaction_id": "TXN-CTBIG"}
    score, rules = calculate_card_testing_score(txn_large, history)
    test("Card testing score >= 70", score >= 70, f"-> score={score}")
    test("Has card testing rule", any("CARD_TESTING" in r for r in rules))


def test_collusion():
    print("\n[6/9] Collusion Detection")
    # Same driver-passenger pair 10 rides
    history = [
        {"user_id": "USR-COL", "driver_id": "DRV-COL",
         "pickup_lat": 6.52, "pickup_lng": 3.38,
         "dropoff_lat": 6.521, "dropoff_lng": 3.381,  # Circular route
         "timestamp": f"2025-02-{10 + i}T10:00:00", "transaction_id": f"TXN-COL{i}"}
        for i in range(10)
    ]
    txn = {"user_id": "USR-COL", "driver_id": "DRV-COL",
           "pickup_lat": 6.52, "pickup_lng": 3.38,
           "dropoff_lat": 6.521, "dropoff_lng": 3.381,
           "timestamp": "2025-02-20T10:00:00", "transaction_id": "TXN-COL-NEW"}
    score, rules = calculate_collusion_score(txn, history)
    test("Collusion score >= 70", score >= 70, f"-> score={score}")
    test("Has collusion rule", any("COLLUSION" in r for r in rules))


def test_account_takeover():
    print("\n[7/9] Account Takeover Detection")
    # User with history in Lagos, now new card in Nairobi
    history = [
        {"user_id": "USR-ATO", "card_last4": "1111", "device_id": "DEV-OLD",
         "pickup_country": "Nigeria", "pickup_city": "Lagos",
         "timestamp": f"2025-02-{10 + i}T10:00:00", "transaction_id": f"TXN-ATO{i}"}
        for i in range(5)
    ]
    txn = {"user_id": "USR-ATO", "card_last4": "9999", "device_id": "DEV-NEW",
           "pickup_country": "Kenya", "pickup_city": "Nairobi",
           "timestamp": "2025-02-18T10:00:00", "transaction_id": "TXN-ATO-NEW"}
    score, rules = calculate_ato_score(txn, history)
    test("ATO score >= 70", score >= 70, f"-> score={score}")
    test("Has ATO rule", any("ATO" in r for r in rules))


def test_fraud_ring():
    print("\n[8/9] Fraud Ring Detection")
    # 4 users sharing 1 device
    history = [
        {"user_id": f"USR-RING-{i}", "device_id": "DEV-SHARED", "amount": 800 + i * 10,
         "timestamp": f"2025-02-15T{10 + i}:00:00", "transaction_id": f"TXN-RING{i}"}
        for i in range(4)
    ]
    txn = {"user_id": "USR-RING-4", "device_id": "DEV-SHARED", "amount": 810,
           "timestamp": "2025-02-15T15:00:00", "transaction_id": "TXN-RING-NEW"}
    score, rules = calculate_fraud_ring_score(txn, history)
    test("Fraud ring score >= 70", score >= 70, f"-> score={score}")
    test("Has fraud ring rule", any("FRAUD_RING" in r for r in rules))


def test_full_pipeline():
    print("\n[9/9] Full Pipeline (CSV Data)")
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "transactions.csv")
    if not os.path.exists(csv_path):
        print("  SKIP  No transactions.csv found (run generate_transactions.py first)")
        return

    df = pd.read_csv(csv_path)
    test("CSV has 1000+ transactions", len(df) >= 1000, f"-> {len(df)}")
    test("Has fraudulent labels", df["is_fraudulent"].sum() > 0,
         f"-> {df['is_fraudulent'].sum()} fraudulent")

    # Process a sample
    sample = df.head(100)
    assessments = process_dataframe(sample)
    test("Pipeline processes transactions", len(assessments) == len(sample))
    test("Has risk_score column", "risk_score" in assessments.columns)
    test("Has risk_level column", "risk_level" in assessments.columns)
    test("Scores in range 0-100",
         assessments["risk_score"].min() >= 0 and assessments["risk_score"].max() <= 100,
         f"-> min={assessments['risk_score'].min()}, max={assessments['risk_score'].max()}")
    test("Has all risk levels",
         set(assessments["risk_level"].unique()).issubset({"low_risk", "medium_risk", "high_risk"}))


def main():
    print("=" * 55)
    print("  OASIS RIDES - PIPELINE UNIT TESTS")
    print("=" * 55)
    print()

    test_haversine()
    test_velocity()
    test_geographic()
    test_amount()
    test_card_testing()
    test_collusion()
    test_account_takeover()
    test_fraud_ring()
    test_full_pipeline()

    print()
    print("=" * 55)
    total = PASS + FAIL
    print(f"  RESULTS: {PASS}/{total} passed, {FAIL} failed")
    print(f"  {'ALL TESTS PASSED!' if FAIL == 0 else f'{FAIL} TESTS FAILED'}")
    print("=" * 55)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Generate 1200+ realistic ride-hailing transactions with planted fraud patterns.
Outputs to data/transactions.csv
"""
import pandas as pd
import numpy as np
import uuid
import random
from datetime import datetime, timedelta
import os
import json

random.seed(42)
np.random.seed(42)

# City data with coordinates and currency
CITIES = {
    "Lagos": {"country": "Nigeria", "lat": 6.5244, "lng": 3.3792, "currency": "NGN",
              "amount_range": (500, 5000), "small_amount": 200, "large_amount": 15000},
    "Abuja": {"country": "Nigeria", "lat": 9.0579, "lng": 7.4951, "currency": "NGN",
              "amount_range": (400, 4500), "small_amount": 150, "large_amount": 12000},
    "Nairobi": {"country": "Kenya", "lat": -1.2921, "lng": 36.8219, "currency": "KES",
                "amount_range": (200, 3000), "small_amount": 80, "large_amount": 8000},
    "Mombasa": {"country": "Kenya", "lat": -4.0435, "lng": 39.6682, "currency": "KES",
                "amount_range": (150, 2500), "small_amount": 60, "large_amount": 7000},
    "Johannesburg": {"country": "South Africa", "lat": -26.2041, "lng": 28.0473, "currency": "ZAR",
                     "amount_range": (50, 500), "small_amount": 20, "large_amount": 1500},
    "Cape Town": {"country": "South Africa", "lat": -33.9249, "lng": 18.4241, "currency": "ZAR",
                  "amount_range": (60, 450), "small_amount": 25, "large_amount": 1200},
}


def random_offset(lat, lng, km_radius=10):
    """Add random offset to coordinates within km_radius."""
    offset_lat = random.uniform(-km_radius / 111, km_radius / 111)
    offset_lng = random.uniform(-km_radius / 111, km_radius / 111)
    return lat + offset_lat, lng + offset_lng


def generate_transaction(user_id, driver_id, card_last4, device_id, city_name, timestamp,
                         amount=None, is_fraudulent=False):
    city = CITIES[city_name]
    pickup_lat, pickup_lng = random_offset(city["lat"], city["lng"])
    dropoff_lat, dropoff_lng = random_offset(city["lat"], city["lng"])

    if amount is None:
        amount = round(random.uniform(*city["amount_range"]), 2)

    distance = round(random.uniform(1, 25), 1)
    duration = int(distance * random.uniform(2, 5))

    return {
        "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
        "timestamp": timestamp.isoformat(),
        "user_id": user_id,
        "driver_id": driver_id,
        "card_last4": card_last4,
        "device_id": device_id,
        "pickup_city": city_name,
        "pickup_country": city["country"],
        "pickup_lat": round(pickup_lat, 6),
        "pickup_lng": round(pickup_lng, 6),
        "dropoff_city": city_name,
        "dropoff_lat": round(dropoff_lat, 6),
        "dropoff_lng": round(dropoff_lng, 6),
        "distance_km": distance,
        "duration_minutes": max(duration, 3),
        "amount": amount,
        "currency": city["currency"],
        "payment_status": "completed",
        "is_fraudulent": is_fraudulent,
    }


def generate_normal_transactions(n=1000):
    """Generate legitimate ride transactions."""
    transactions = []
    base_time = datetime(2025, 2, 14, 6, 0, 0)

    users = [f"USR-{i:04d}" for i in range(1, 201)]
    drivers = [f"DRV-{i:04d}" for i in range(1, 81)]
    cards = [f"{random.randint(1000, 9999)}" for _ in range(200)]
    devices = [f"DEV-{uuid.uuid4().hex[:8]}" for _ in range(180)]

    city_names = list(CITIES.keys())
    city_weights = [0.30, 0.10, 0.25, 0.08, 0.17, 0.10]  # Lagos heaviest

    for i in range(n):
        user_idx = random.randint(0, len(users) - 1)
        user_id = users[user_idx]
        driver_id = random.choice(drivers)
        card = cards[user_idx]
        device = devices[min(user_idx, len(devices) - 1)]
        city = random.choices(city_names, weights=city_weights, k=1)[0]

        hours_offset = random.uniform(0, 168)  # 7 days
        ts = base_time + timedelta(hours=hours_offset)
        # Realistic hours: mostly 6am-11pm
        if ts.hour < 6:
            ts = ts.replace(hour=random.randint(6, 22))

        transactions.append(generate_transaction(user_id, driver_id, card, device, city, ts))

    return transactions, users, drivers, cards, devices


def generate_card_testing_fraud(base_time):
    """6 cards with small transactions followed by large ones."""
    transactions = []

    for i in range(6):
        user_id = f"USR-CT-{i:02d}"
        card = f"{random.randint(1000, 9999)}"
        device = f"DEV-CT-{uuid.uuid4().hex[:8]}"
        city = random.choice(["Lagos", "Nairobi", "Johannesburg"])
        driver = f"DRV-{random.randint(1, 80):04d}"
        small_amount = CITIES[city]["small_amount"]
        large_amount = CITIES[city]["large_amount"]

        # 3-5 small transactions
        num_small = random.randint(3, 5)
        start_time = base_time + timedelta(hours=random.uniform(0, 120))

        for j in range(num_small):
            ts = start_time + timedelta(minutes=random.randint(5, 30) * (j + 1))
            amount = round(random.uniform(small_amount * 0.3, small_amount), 2)
            transactions.append(
                generate_transaction(user_id, driver, card, device, city, ts,
                                     amount=amount, is_fraudulent=True)
            )

        # 1-2 large transactions
        for j in range(random.randint(1, 2)):
            ts = start_time + timedelta(hours=random.uniform(1, 4))
            amount = round(random.uniform(large_amount * 0.8, large_amount * 1.5), 2)
            transactions.append(
                generate_transaction(user_id, driver, card, device, city, ts,
                                     amount=amount, is_fraudulent=True)
            )

    return transactions


def generate_velocity_fraud(base_time):
    """4 users with 10-15 transactions in a 2-hour window."""
    transactions = []

    for i in range(4):
        user_id = f"USR-VEL-{i:02d}"
        card = f"{random.randint(1000, 9999)}"
        device = f"DEV-VEL-{uuid.uuid4().hex[:8]}"
        city = random.choice(["Lagos", "Abuja", "Nairobi", "Johannesburg"])
        num_txns = random.randint(10, 15)
        start_time = base_time + timedelta(hours=random.uniform(24, 96))

        for j in range(num_txns):
            ts = start_time + timedelta(minutes=random.randint(1, 10) * (j + 1))
            driver = f"DRV-{random.randint(1, 80):04d}"
            transactions.append(
                generate_transaction(user_id, driver, card, device, city, ts,
                                     is_fraudulent=True)
            )

    return transactions


def generate_geographic_anomalies(base_time):
    """3 users with transactions in different countries within impossible timeframes."""
    transactions = []
    impossible_pairs = [
        ("Lagos", "Nairobi"),      # ~3,500 km apart
        ("Johannesburg", "Lagos"),  # ~5,000 km apart
        ("Cape Town", "Abuja"),     # ~5,500 km apart
    ]

    for i, (city1, city2) in enumerate(impossible_pairs):
        user_id = f"USR-GEO-{i:02d}"
        card = f"{random.randint(1000, 9999)}"
        device = f"DEV-GEO-{uuid.uuid4().hex[:8]}"
        start_time = base_time + timedelta(hours=random.uniform(48, 120))

        # Transaction in city1
        driver1 = f"DRV-{random.randint(1, 80):04d}"
        transactions.append(
            generate_transaction(user_id, driver1, card, device, city1, start_time,
                                 is_fraudulent=True)
        )

        # Transaction in city2 just 15 minutes later (impossible)
        ts2 = start_time + timedelta(minutes=15)
        driver2 = f"DRV-{random.randint(1, 80):04d}"
        transactions.append(
            generate_transaction(user_id, driver2, card, device, city2, ts2,
                                 is_fraudulent=True)
        )

    return transactions


def generate_collusion_patterns(base_time):
    """3 driver-passenger pairs with 8-12 rides in a week, circular routes."""
    transactions = []

    for i in range(3):
        user_id = f"USR-COL-{i:02d}"
        driver_id = f"DRV-COL-{i:02d}"
        card = f"{random.randint(1000, 9999)}"
        device = f"DEV-COL-{uuid.uuid4().hex[:8]}"
        city = random.choice(["Lagos", "Nairobi", "Johannesburg"])
        num_rides = random.randint(8, 12)

        for j in range(num_rides):
            ts = base_time + timedelta(hours=random.uniform(0, 168))
            city_data = CITIES[city]
            # Circular route: dropoff ~= pickup
            pickup_lat, pickup_lng = random_offset(city_data["lat"], city_data["lng"], km_radius=2)

            txn = generate_transaction(user_id, driver_id, card, device, city, ts,
                                       is_fraudulent=True)
            # Make it circular
            txn["dropoff_lat"] = round(pickup_lat + random.uniform(-0.002, 0.002), 6)
            txn["dropoff_lng"] = round(pickup_lng + random.uniform(-0.002, 0.002), 6)
            txn["pickup_lat"] = round(pickup_lat, 6)
            txn["pickup_lng"] = round(pickup_lng, 6)
            transactions.append(txn)

    return transactions


def generate_account_takeover(base_time):
    """2 users with new card + new location within 30 minutes."""
    transactions = []

    for i in range(2):
        user_id = f"USR-ATO-{i:02d}"
        original_card = f"{random.randint(1000, 9999)}"
        new_card = f"{random.randint(1000, 9999)}"
        device = f"DEV-ATO-{uuid.uuid4().hex[:8]}"
        original_city = "Lagos" if i == 0 else "Johannesburg"
        new_city = "Nairobi" if i == 0 else "Cape Town"

        # Normal transactions first (past week)
        for j in range(5):
            ts = base_time + timedelta(hours=random.uniform(0, 120))
            driver = f"DRV-{random.randint(1, 80):04d}"
            transactions.append(
                generate_transaction(user_id, driver, original_card, device, original_city, ts)
            )

        # Suspicious: new card + new country within 30 min
        ato_time = base_time + timedelta(hours=130)
        driver = f"DRV-{random.randint(1, 80):04d}"
        new_device = f"DEV-ATO-NEW-{uuid.uuid4().hex[:8]}"
        transactions.append(
            generate_transaction(user_id, driver, new_card, new_device, new_city, ato_time,
                                 is_fraudulent=True)
        )
        # Second suspicious transaction
        ts2 = ato_time + timedelta(minutes=15)
        transactions.append(
            generate_transaction(user_id, driver, new_card, new_device, new_city, ts2,
                                 is_fraudulent=True)
        )

    return transactions


def generate_fraud_ring(base_time):
    """5 users sharing 2 devices, similar small amounts, same time windows."""
    transactions = []
    shared_devices = [f"DEV-RING-{uuid.uuid4().hex[:8]}" for _ in range(2)]
    ring_users = [f"USR-RING-{i:02d}" for i in range(5)]
    ring_cards = [f"{random.randint(1000, 9999)}" for _ in range(5)]
    city = "Lagos"

    for i, user_id in enumerate(ring_users):
        device = shared_devices[i % 2]
        card = ring_cards[i]

        for j in range(4):  # 4 transactions each
            ts = base_time + timedelta(hours=random.uniform(60, 72))  # All within same 12h window
            driver = f"DRV-{random.randint(1, 80):04d}"
            base_amount = 800  # Similar amounts
            amount = round(base_amount + random.uniform(-100, 100), 2)
            transactions.append(
                generate_transaction(user_id, driver, card, device, city, ts,
                                     amount=amount, is_fraudulent=True)
            )

    return transactions


def main():
    base_time = datetime(2025, 2, 14, 6, 0, 0)

    print("Generating normal transactions...")
    normal_txns, users, drivers, cards, devices = generate_normal_transactions(1000)

    print("Generating card testing fraud...")
    card_testing = generate_card_testing_fraud(base_time)

    print("Generating velocity fraud...")
    velocity = generate_velocity_fraud(base_time)

    print("Generating geographic anomalies...")
    geo_anomalies = generate_geographic_anomalies(base_time)

    print("Generating collusion patterns...")
    collusion = generate_collusion_patterns(base_time)

    print("Generating account takeover...")
    ato = generate_account_takeover(base_time)

    print("Generating fraud ring...")
    fraud_ring = generate_fraud_ring(base_time)

    all_transactions = (normal_txns + card_testing + velocity + geo_anomalies +
                        collusion + ato + fraud_ring)

    random.shuffle(all_transactions)

    df = pd.DataFrame(all_transactions)
    df = df.sort_values("timestamp").reset_index(drop=True)

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "transactions.csv")
    df.to_csv(output_path, index=False)

    total = len(df)
    fraudulent = df["is_fraudulent"].sum()
    print(f"\nGenerated {total} transactions ({fraudulent} fraudulent, {total - fraudulent} legitimate)")
    print(f"  Card testing: {len(card_testing)} transactions")
    print(f"  Velocity fraud: {len(velocity)} transactions")
    print(f"  Geographic anomalies: {len(geo_anomalies)} transactions")
    print(f"  Collusion: {len(collusion)} transactions")
    print(f"  Account takeover: {len(ato)} transactions")
    print(f"  Fraud ring: {len(fraud_ring)} transactions")
    print(f"\nSaved to {output_path}")

    return df


if __name__ == "__main__":
    main()

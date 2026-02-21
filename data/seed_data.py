"""Seed generated transaction data into Supabase."""
import pandas as pd
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_supabase


def seed_transactions(csv_path: str = None, batch_size: int = 50):
    """Load transactions from CSV and insert into Supabase."""
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions.csv")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run generate_transactions.py first.")
        return

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} transactions from {csv_path}")

    client = get_supabase()

    # Insert in batches
    total = len(df)
    for i in range(0, total, batch_size):
        batch = df.iloc[i:i + batch_size].to_dict("records")

        # Clean data types
        for record in batch:
            record["is_fraudulent"] = bool(record.get("is_fraudulent", False))
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None

        try:
            client.table("transactions").insert(batch).execute()
            print(f"  Inserted batch {i // batch_size + 1} ({min(i + batch_size, total)}/{total})")
        except Exception as e:
            print(f"  Error on batch {i // batch_size + 1}: {e}")

    print(f"\nSeeding complete! {total} transactions inserted.")


if __name__ == "__main__":
    seed_transactions()

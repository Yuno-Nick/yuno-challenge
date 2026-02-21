"""Transaction stream simulator: reads CSV and emits batches."""
import pandas as pd
import time
import os
from typing import Generator

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "transactions.csv")


class TransactionStream:
    """Simulates a real-time transaction stream from CSV data."""

    def __init__(self, csv_path: str = None, batch_size: int = 10):
        self.csv_path = csv_path or DATA_PATH
        self.batch_size = batch_size
        self.current_index = 0
        self.df = None
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.csv_path):
            self.df = pd.read_csv(self.csv_path)
            self.df = self.df.sort_values("timestamp").reset_index(drop=True)
        else:
            self.df = pd.DataFrame()

    def get_next_batch(self) -> list[dict]:
        """Get the next batch of transactions."""
        if self.df is None or self.df.empty:
            self._load_data()
            if self.df is None or self.df.empty:
                return []

        if self.current_index >= len(self.df):
            return []  # Stream exhausted

        end_index = min(self.current_index + self.batch_size, len(self.df))
        batch = self.df.iloc[self.current_index:end_index].to_dict("records")
        self.current_index = end_index
        return batch

    def get_all_processed(self) -> list[dict]:
        """Get all transactions processed so far."""
        if self.df is None or self.df.empty:
            return []
        return self.df.iloc[:self.current_index].to_dict("records")

    def reset(self):
        """Reset stream to beginning."""
        self.current_index = 0

    @property
    def total_transactions(self) -> int:
        return len(self.df) if self.df is not None else 0

    @property
    def processed_count(self) -> int:
        return self.current_index

    @property
    def is_exhausted(self) -> bool:
        return self.current_index >= self.total_transactions

    @property
    def progress(self) -> float:
        if self.total_transactions == 0:
            return 0
        return self.current_index / self.total_transactions

"""
Synthetic payment transaction generator.

Generates realistic-looking payment transaction data for
development and machine-learning experimentation.

The generated dataset is synthetic and contains no real
customer or payment information.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEED = 42
NUM_TRANSACTIONS = 100_000

OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "payments.csv"

fake = Faker("en_IN")
Faker.seed(SEED)
random.seed(SEED)
np.random.seed(SEED)


# ---------------------------------------------------------------------------
# Reference values
# ---------------------------------------------------------------------------

PAYMENT_METHODS = [
    "UPI",
    "CARD",
    "NETBANKING",
    "WALLET",
]

PAYMENT_METHOD_WEIGHTS = [
    0.50,
    0.30,
    0.15,
    0.05,
]

FAILURE_REASONS = [
    "TIMEOUT",
    "BANK_DECLINE",
    "INSUFFICIENT_FUNDS",
    "AUTHENTICATION_FAILURE",
    "NETWORK_ERROR",
    "CARD_DECLINE",
    "EXPIRED_PAYMENT_METHOD",
]

FAILURE_REASON_WEIGHTS = [
    0.20,
    0.18,
    0.20,
    0.12,
    0.12,
    0.10,
    0.08,
]

CURRENCIES = ["INR"]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_customer_id() -> str:
    """Generate a synthetic customer identifier."""
    return f"CUST_{random.randint(1, 25_000):05d}"


def generate_transaction_amount() -> float:
    """
    Generate a realistic transaction amount.

    Most transactions are relatively small, while a smaller
    number of transactions have higher values.
    """
    amount = np.random.lognormal(mean=7.2, sigma=0.9)

    # Keep values within a reasonable demo range.
    amount = min(max(amount, 100), 250_000)

    return round(float(amount), 2)


def generate_transaction_timestamp() -> datetime:
    """Generate a timestamp within the previous 90 days."""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=90)

    random_seconds = random.randint(
        0,
        int((end_time - start_time).total_seconds()),
    )

    return start_time + timedelta(seconds=random_seconds)


def generate_payment_status() -> str:
    """
    Generate payment status.

    The initial dataset intentionally contains a realistic
    mixture of successful and failed transactions.
    """
    return random.choices(
        ["SUCCESS", "FAILED"],
        weights=[0.74, 0.26],
        k=1,
    )[0]


def generate_failure_reason(status: str) -> str | None:
    """Generate a failure reason only for failed payments."""
    if status == "SUCCESS":
        return None

    return random.choices(
        FAILURE_REASONS,
        weights=FAILURE_REASON_WEIGHTS,
        k=1,
    )[0]


def generate_retry_count(status: str) -> int:
    """
    Generate the number of previous retry attempts.

    Successful payments generally have fewer retries,
    while failed payments can have several attempts.
    """
    if status == "SUCCESS":
        return random.choices(
            [0, 1, 2],
            weights=[0.75, 0.20, 0.05],
            k=1,
        )[0]

    return random.choices(
        [0, 1, 2, 3, 4],
        weights=[0.35, 0.30, 0.20, 0.10, 0.05],
        k=1,
    )[0]


def generate_subscription_status() -> str:
    """Generate a synthetic subscription state."""
    return random.choices(
        ["ACTIVE", "INACTIVE", "NOT_SUBSCRIBED"],
        weights=[0.35, 0.20, 0.45],
        k=1,
    )[0]


# ---------------------------------------------------------------------------
# Transaction generation
# ---------------------------------------------------------------------------

def generate_transaction(index: int) -> dict:
    """Generate one synthetic payment transaction."""

    status = generate_payment_status()
    timestamp = generate_transaction_timestamp()

    return {
        "transaction_id": f"TXN_{index:07d}",
        "customer_id": generate_customer_id(),
        "amount": generate_transaction_amount(),
        "currency": random.choice(CURRENCIES),
        "payment_method": random.choices(
            PAYMENT_METHODS,
            weights=PAYMENT_METHOD_WEIGHTS,
            k=1,
        )[0],
        "timestamp": timestamp,
        "status": status,
        "failure_reason": generate_failure_reason(status),
        "retry_count": generate_retry_count(status),
        "subscription_status": generate_subscription_status(),
    }


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------

def generate_dataset(num_transactions: int) -> pd.DataFrame:
    """Generate a complete synthetic payment dataset."""

    print(f"Generating {num_transactions:,} synthetic transactions...")

    transactions = [
        generate_transaction(index)
        for index in range(1, num_transactions + 1)
    ]

    dataframe = pd.DataFrame(transactions)

    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"])

    dataframe = dataframe.sort_values(
        by="timestamp"
    ).reset_index(drop=True)

    return dataframe


def validate_dataset(dataframe: pd.DataFrame) -> None:
    """Perform basic dataset validation."""

    required_columns = {
        "transaction_id",
        "customer_id",
        "amount",
        "currency",
        "payment_method",
        "timestamp",
        "status",
        "failure_reason",
        "retry_count",
        "subscription_status",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if dataframe["transaction_id"].duplicated().any():
        raise ValueError("Duplicate transaction IDs detected.")

    if (dataframe["amount"] <= 0).any():
        raise ValueError("Transaction amounts must be positive.")

    if not dataframe["status"].isin(
        ["SUCCESS", "FAILED"]
    ).all():
        raise ValueError("Invalid payment status detected.")

    failed_without_reason = dataframe[
        (dataframe["status"] == "FAILED")
        & (dataframe["failure_reason"].isna())
    ]

    if not failed_without_reason.empty:
        raise ValueError(
            "Failed payments must have a failure reason."
        )

    successful_with_reason = dataframe[
        (dataframe["status"] == "SUCCESS")
        & (dataframe["failure_reason"].notna())
    ]

    if not successful_with_reason.empty:
        raise ValueError(
            "Successful payments must not have a failure reason."
        )

    print("Dataset validation passed.")


def print_summary(dataframe: pd.DataFrame) -> None:
    """Print useful statistics about the generated dataset."""

    total = len(dataframe)
    successful = (dataframe["status"] == "SUCCESS").sum()
    failed = (dataframe["status"] == "FAILED").sum()

    success_rate = successful / total * 100
    failure_rate = failed / total * 100

    print("\nDataset Summary")
    print("-" * 40)
    print(f"Total transactions : {total:,}")
    print(f"Successful         : {successful:,} ({success_rate:.2f}%)")
    print(f"Failed             : {failed:,} ({failure_rate:.2f}%)")
    print(
        f"Total transaction value : "
        f"₹{dataframe['amount'].sum():,.2f}"
    )

    print("\nPayment methods")
    print(dataframe["payment_method"].value_counts())

    print("\nFailure reasons")
    print(
        dataframe.loc[
            dataframe["status"] == "FAILED",
            "failure_reason",
        ].value_counts()
    )


def main() -> None:
    """Generate, validate, and save the dataset."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataframe = generate_dataset(NUM_TRANSACTIONS)

    validate_dataset(dataframe)

    dataframe.to_csv(OUTPUT_FILE, index=False)

    print_summary(dataframe)

    print(f"\nDataset saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
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


# ---------------------------------------------------------------------------
# Failure patterns
# ---------------------------------------------------------------------------

FAILURE_PATTERNS = {
    "UPI": {
        "TIMEOUT": 0.25,
        "BANK_DECLINE": 0.20,
        "INSUFFICIENT_FUNDS": 0.18,
        "NETWORK_ERROR": 0.18,
        "AUTHENTICATION_FAILURE": 0.10,
        "CARD_DECLINE": 0.00,
        "EXPIRED_PAYMENT_METHOD": 0.09,
    },
    "CARD": {
        "TIMEOUT": 0.10,
        "BANK_DECLINE": 0.15,
        "INSUFFICIENT_FUNDS": 0.25,
        "NETWORK_ERROR": 0.08,
        "AUTHENTICATION_FAILURE": 0.15,
        "CARD_DECLINE": 0.20,
        "EXPIRED_PAYMENT_METHOD": 0.07,
    },
    "NETBANKING": {
        "TIMEOUT": 0.18,
        "BANK_DECLINE": 0.25,
        "INSUFFICIENT_FUNDS": 0.18,
        "NETWORK_ERROR": 0.18,
        "AUTHENTICATION_FAILURE": 0.15,
        "CARD_DECLINE": 0.00,
        "EXPIRED_PAYMENT_METHOD": 0.06,
    },
    "WALLET": {
        "TIMEOUT": 0.15,
        "BANK_DECLINE": 0.15,
        "INSUFFICIENT_FUNDS": 0.30,
        "NETWORK_ERROR": 0.20,
        "AUTHENTICATION_FAILURE": 0.12,
        "CARD_DECLINE": 0.00,
        "EXPIRED_PAYMENT_METHOD": 0.08,
    },
}


FAILURE_CATEGORIES = {
    "TIMEOUT": "TEMPORARY",
    "NETWORK_ERROR": "TEMPORARY",
    "BANK_DECLINE": "TEMPORARY",
    "INSUFFICIENT_FUNDS": "PERMANENT",
    "AUTHENTICATION_FAILURE": "PERMANENT",
    "CARD_DECLINE": "PERMANENT",
    "EXPIRED_PAYMENT_METHOD": "PERMANENT",
}


# ---------------------------------------------------------------------------
# Recovery outcome configuration
# ---------------------------------------------------------------------------

RECOVERY_BASE_PROBABILITY = {
    "TIMEOUT": 0.75,
    "NETWORK_ERROR": 0.70,
    "BANK_DECLINE": 0.55,
    "INSUFFICIENT_FUNDS": 0.45,
    "AUTHENTICATION_FAILURE": 0.30,
    "CARD_DECLINE": 0.35,
    "EXPIRED_PAYMENT_METHOD": 0.15,
}


# ---------------------------------------------------------------------------
# Customer profiles
# ---------------------------------------------------------------------------

NUM_CUSTOMERS = 25_000


def generate_customer_profiles() -> dict:
    """
    Generate persistent customer-level attributes.

    Each customer receives a profile that remains consistent
    across multiple transactions.
    """

    profiles = {}

    for customer_number in range(1, NUM_CUSTOMERS + 1):
        customer_id = f"CUST_{customer_number:05d}"

        profiles[customer_id] = {
            "customer_age_days": random.randint(30, 1_500),
            "subscription_status": random.choices(
                ["ACTIVE", "INACTIVE", "NOT_SUBSCRIBED"],
                weights=[0.35, 0.20, 0.45],
                k=1,
            )[0],
            "is_recurring_customer": random.choices(
                [True, False],
                weights=[0.35, 0.65],
                k=1,
            )[0],
        }

    return profiles


CUSTOMER_PROFILES = generate_customer_profiles()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_customer_id() -> str:
    """Select an existing customer from the generated profiles."""

    return random.choice(list(CUSTOMER_PROFILES.keys()))


def generate_transaction_amount() -> float:
    """
    Generate a realistic transaction amount.

    Most transactions are relatively small, while a smaller
    number of transactions have higher values.
    """

    amount = np.random.lognormal(
        mean=7.2,
        sigma=0.9,
    )

    amount = min(
        max(amount, 100),
        250_000,
    )

    return round(float(amount), 2)


def generate_transaction_timestamp() -> datetime:
    """Generate a timestamp within the previous 90 days."""

    end_time = datetime.now()
    start_time = end_time - timedelta(days=90)

    random_seconds = random.randint(
        0,
        int(
            (end_time - start_time).total_seconds()
        ),
    )

    return start_time + timedelta(
        seconds=random_seconds
    )


def generate_payment_status() -> str:
    """Generate a realistic payment status."""

    return random.choices(
        ["SUCCESS", "FAILED"],
        weights=[0.74, 0.26],
        k=1,
    )[0]


def generate_failure_reason(
    status: str,
    payment_method: str,
) -> str | None:
    """Generate a failure reason based on the payment method."""

    if status == "SUCCESS":
        return None

    patterns = FAILURE_PATTERNS[payment_method]

    reasons = list(patterns.keys())
    weights = list(patterns.values())

    return random.choices(
        reasons,
        weights=weights,
        k=1,
    )[0]


def generate_failure_category(
    failure_reason: str | None,
) -> str | None:
    """Classify a failure as temporary or permanent."""

    if failure_reason is None:
        return None

    return FAILURE_CATEGORIES[failure_reason]


def generate_retry_count(status: str) -> int:
    """Generate the number of previous retry attempts."""

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


# ---------------------------------------------------------------------------
# Recovery functions
# ---------------------------------------------------------------------------

def calculate_recovery_probability(
    failure_reason: str | None,
    subscription_status: str,
    is_recurring_customer: bool,
    customer_success_rate: float,
) -> float | None:
    """
    Estimate the probability that a failed payment can eventually
    be recovered.

    Successful payments receive no recovery probability.
    """

    # Pandas converts None to NaN inside DataFrames.
    # Both None and NaN should mean that no recovery prediction
    # is required.
    if pd.isna(failure_reason):
        return None

    probability = RECOVERY_BASE_PROBABILITY[failure_reason]

    # Active subscribers are more valuable recovery targets.
    if subscription_status == "ACTIVE":
        probability += 0.10

    # Recurring customers have demonstrated payment intent.
    if is_recurring_customer:
        probability += 0.08

    # Strong historical payment behavior increases recovery likelihood.
    if customer_success_rate >= 0.80:
        probability += 0.10
    elif customer_success_rate >= 0.60:
        probability += 0.05
    elif customer_success_rate < 0.30:
        probability -= 0.10

    return max(
        0.05,
        min(probability, 0.95),
    )


def generate_recovery_outcome(
    recovery_probability: float | None,
) -> int | None:
    """
    Generate the synthetic recovery outcome.

    1 = recovered
    0 = not recovered
    """

    if recovery_probability is None:
        return None

    return int(
        random.random() < recovery_probability
    )


# ---------------------------------------------------------------------------
# Transaction generation
# ---------------------------------------------------------------------------

def generate_transaction(index: int) -> dict:
    """Generate one synthetic payment transaction."""

    status = generate_payment_status()
    timestamp = generate_transaction_timestamp()

    customer_id = generate_customer_id()
    customer_profile = CUSTOMER_PROFILES[customer_id]

    payment_method = random.choices(
        PAYMENT_METHODS,
        weights=PAYMENT_METHOD_WEIGHTS,
        k=1,
    )[0]

    failure_reason = generate_failure_reason(
        status,
        payment_method,
    )

    return {
        "transaction_id": f"TXN_{index:07d}",
        "customer_id": customer_id,
        "customer_age_days": customer_profile[
            "customer_age_days"
        ],
        "amount": generate_transaction_amount(),
        "currency": "INR",
        "payment_method": payment_method,
        "timestamp": timestamp,
        "status": status,
        "failure_reason": failure_reason,
        "failure_category": generate_failure_category(
            failure_reason
        ),
        "retry_count": generate_retry_count(status),
        "subscription_status": customer_profile[
            "subscription_status"
        ],
        "is_recurring_customer": customer_profile[
            "is_recurring_customer"
        ],
    }


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------

def generate_dataset(
    num_transactions: int,
) -> pd.DataFrame:
    """Generate a complete synthetic payment dataset."""

    print(
        f"Generating {num_transactions:,} "
        "synthetic transactions..."
    )

    transactions = [
        generate_transaction(index)
        for index in range(
            1,
            num_transactions + 1,
        )
    ]

    dataframe = pd.DataFrame(transactions)

    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"]
    )

    # Sort chronologically so historical features only use
    # information available before the current transaction.
    dataframe = dataframe.sort_values(
        by="timestamp"
    ).reset_index(drop=True)

    # -----------------------------------------------------------------------
    # Customer historical behavior
    # -----------------------------------------------------------------------

    dataframe["previous_successful_payments"] = (
        dataframe.groupby("customer_id")["status"]
        .transform(
            lambda series: (
                series.eq("SUCCESS")
                .cumsum()
                .shift(fill_value=0)
            )
        )
    )

    dataframe["previous_failed_payments"] = (
        dataframe.groupby("customer_id")["status"]
        .transform(
            lambda series: (
                series.eq("FAILED")
                .cumsum()
                .shift(fill_value=0)
            )
        )
    )

    total_previous_payments = (
        dataframe["previous_successful_payments"]
        + dataframe["previous_failed_payments"]
    )

    dataframe["customer_success_rate"] = np.where(
        total_previous_payments > 0,
        dataframe["previous_successful_payments"]
        / total_previous_payments,
        0.0,
    )

    dataframe["customer_success_rate"] = (
        dataframe["customer_success_rate"]
        .round(4)
    )

    # -----------------------------------------------------------------------
    # Recovery probability
    # -----------------------------------------------------------------------

    dataframe["recovery_probability"] = dataframe.apply(
        lambda row: calculate_recovery_probability(
            row["failure_reason"],
            row["subscription_status"],
            row["is_recurring_customer"],
            row["customer_success_rate"],
        ),
        axis=1,
    )

    # -----------------------------------------------------------------------
    # Recovery outcome
    # -----------------------------------------------------------------------

    dataframe["recovered"] = dataframe[
        "recovery_probability"
    ].apply(
        generate_recovery_outcome
    )

    # Explicitly remove recovery labels from successful
    # transactions.
    dataframe.loc[
        dataframe["status"] == "SUCCESS",
        "recovery_probability",
    ] = np.nan

    dataframe.loc[
        dataframe["status"] == "SUCCESS",
        "recovered",
    ] = np.nan

    return dataframe


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """Perform basic dataset validation."""

    required_columns = {
        "transaction_id",
        "customer_id",
        "customer_age_days",
        "amount",
        "currency",
        "payment_method",
        "timestamp",
        "status",
        "failure_reason",
        "failure_category",
        "retry_count",
        "subscription_status",
        "is_recurring_customer",
        "previous_successful_payments",
        "previous_failed_payments",
        "customer_success_rate",
        "recovery_probability",
        "recovered",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if dataframe["transaction_id"].duplicated().any():
        raise ValueError(
            "Duplicate transaction IDs detected."
        )

    if (dataframe["amount"] <= 0).any():
        raise ValueError(
            "Transaction amounts must be positive."
        )

    if not dataframe["status"].isin(
        ["SUCCESS", "FAILED"]
    ).all():
        raise ValueError(
            "Invalid payment status detected."
        )

    failed_without_reason = dataframe[
        (dataframe["status"] == "FAILED")
        & dataframe["failure_reason"].isna()
    ]

    if not failed_without_reason.empty:
        raise ValueError(
            "Failed payments must have a failure reason."
        )

    successful_with_reason = dataframe[
        (dataframe["status"] == "SUCCESS")
        & dataframe["failure_reason"].notna()
    ]

    if not successful_with_reason.empty:
        raise ValueError(
            "Successful payments must not have a failure reason."
        )

    # -----------------------------------------------------------------------
    # Customer history validation
    # -----------------------------------------------------------------------

    if (dataframe["customer_age_days"] <= 0).any():
        raise ValueError(
            "Customer age must be positive."
        )

    if (
        dataframe["previous_successful_payments"]
        < 0
    ).any():
        raise ValueError(
            "Previous successful payment count "
            "cannot be negative."
        )

    if (
        dataframe["previous_failed_payments"]
        < 0
    ).any():
        raise ValueError(
            "Previous failed payment count "
            "cannot be negative."
        )

    if not dataframe[
        "customer_success_rate"
    ].between(0, 1).all():
        raise ValueError(
            "Customer success rate must be between 0 and 1."
        )

    # -----------------------------------------------------------------------
    # Recovery validation
    # -----------------------------------------------------------------------

    recovery_probabilities = dataframe[
        "recovery_probability"
    ].dropna()

    if not recovery_probabilities.between(
        0,
        1,
    ).all():
        raise ValueError(
            "Recovery probability must be between 0 and 1."
        )

    valid_recovery_values = {0, 1}

    invalid_recovery_values = dataframe[
        dataframe["recovered"].notna()
        & ~dataframe["recovered"].isin(
            valid_recovery_values
        )
    ]

    if not invalid_recovery_values.empty:
        raise ValueError(
            "Recovery outcome must be either 0 or 1."
        )

    # Every failed payment must have a recovery probability
    # and a recovery outcome.
    failed_without_recovery = dataframe[
        (dataframe["status"] == "FAILED")
        & (
            dataframe["recovery_probability"].isna()
            | dataframe["recovered"].isna()
        )
    ]

    if not failed_without_recovery.empty:
        raise ValueError(
            "Failed payments must have recovery labels."
        )

    # Successful payments must not have recovery probability
    # or recovery outcomes.
    successful_with_recovery = dataframe[
        (dataframe["status"] == "SUCCESS")
        & (
            dataframe["recovery_probability"].notna()
            | dataframe["recovered"].notna()
        )
    ]

    if not successful_with_recovery.empty:
        raise ValueError(
            "Successful payments must not have recovery labels."
        )

    print("Dataset validation passed.")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(
    dataframe: pd.DataFrame,
) -> None:
    """Print useful statistics about the generated dataset."""

    total = len(dataframe)

    successful = (
        dataframe["status"] == "SUCCESS"
    ).sum()

    failed = (
        dataframe["status"] == "FAILED"
    ).sum()

    success_rate = successful / total * 100
    failure_rate = failed / total * 100

    print("\nDataset Summary")
    print("-" * 40)

    print(
        f"Total transactions      : {total:,}"
    )

    print(
        f"Successful              : "
        f"{successful:,} ({success_rate:.2f}%)"
    )

    print(
        f"Failed                  : "
        f"{failed:,} ({failure_rate:.2f}%)"
    )

    print(
        f"Total transaction value : "
        f"₹{dataframe['amount'].sum():,.2f}"
    )

    print("\nPayment methods")

    print(
        dataframe["payment_method"]
        .value_counts()
        .to_string()
    )

    failed_data = dataframe[
        dataframe["status"] == "FAILED"
    ]

    print("\nFailure reasons")

    print(
        failed_data["failure_reason"]
        .value_counts()
        .to_string()
    )

    print("\nFailure categories")

    print(
        failed_data["failure_category"]
        .value_counts()
        .to_string()
    )

    print("\nRecovery outcomes")

    recovery_counts = (
        failed_data["recovered"]
        .value_counts()
    )

    print(
        f"Recoverable   : "
        f"{recovery_counts.get(1, 0):,}"
    )

    print(
        f"Not recovered : "
        f"{recovery_counts.get(0, 0):,}"
    )

    print("\nAverage recovery probability")

    print(
        f"{failed_data['recovery_probability'].mean():.2%}"
    )

    print("\nFailure reasons by payment method")

    print(
        pd.crosstab(
            failed_data["payment_method"],
            failed_data["failure_reason"],
        ).to_string()
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate, validate, and save the dataset."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = generate_dataset(
        NUM_TRANSACTIONS
    )

    validate_dataset(dataframe)

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print_summary(dataframe)

    print(
        f"\nDataset saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
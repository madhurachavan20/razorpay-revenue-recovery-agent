"""
Feature engineering pipeline for the revenue recovery model.

Transforms raw payment transactions into ML-ready features.

Input:
    data/payments.csv

Output:
    ml/dataset/recovery_features.csv
"""

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_FILE = Path("data/payments.csv")
OUTPUT_DIR = Path("ml/dataset")
OUTPUT_FILE = OUTPUT_DIR / "recovery_features.csv"


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def create_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Create machine-learning features from payment data.

    Only information available at the time of the failed
    payment should be used as a feature.
    """

    features = dataframe.copy()

    # -----------------------------------------------------------------------
    # Payment amount features
    # -----------------------------------------------------------------------

    features["amount_log"] = (
        features["amount"]
        .clip(lower=1)
        .apply(lambda value: __import__("math").log1p(value))
    )

    # -----------------------------------------------------------------------
    # Customer history features
    # -----------------------------------------------------------------------

    features["total_previous_payments"] = (
        features["previous_successful_payments"]
        + features["previous_failed_payments"]
    )

    features["previous_failure_rate"] = (
        features["previous_failed_payments"]
        / features["total_previous_payments"].replace(
            0,
            1,
        )
    )

    # -----------------------------------------------------------------------
    # Retry behavior
    # -----------------------------------------------------------------------

    features["has_previous_retry"] = (
        features["retry_count"] > 0
    ).astype(int)

    # -----------------------------------------------------------------------
    # Customer characteristics
    # -----------------------------------------------------------------------

    features["is_active_subscription"] = (
        features["subscription_status"] == "ACTIVE"
    ).astype(int)

    features["is_inactive_subscription"] = (
        features["subscription_status"] == "INACTIVE"
    ).astype(int)

    features["is_not_subscribed"] = (
        features["subscription_status"]
        == "NOT_SUBSCRIBED"
    ).astype(int)

    features["is_recurring_customer"] = (
        features["is_recurring_customer"]
        .astype(int)
    )

    # -----------------------------------------------------------------------
    # Payment method encoding
    # -----------------------------------------------------------------------

    payment_method_dummies = pd.get_dummies(
        features["payment_method"],
        prefix="payment_method",
        dtype=int,
    )

    features = pd.concat(
        [
            features,
            payment_method_dummies,
        ],
        axis=1,
    )

    # -----------------------------------------------------------------------
    # Failure category encoding
    # -----------------------------------------------------------------------

    features["is_temporary_failure"] = (
        features["failure_category"]
        == "TEMPORARY"
    ).astype(int)

    features["is_permanent_failure"] = (
        features["failure_category"]
        == "PERMANENT"
    ).astype(int)

    # -----------------------------------------------------------------------
    # Time-based features
    # -----------------------------------------------------------------------

    features["timestamp"] = pd.to_datetime(
        features["timestamp"]
    )

    features["transaction_hour"] = (
        features["timestamp"].dt.hour
    )

    features["transaction_day_of_week"] = (
        features["timestamp"].dt.dayofweek
    )

    features["is_weekend"] = (
        features["transaction_day_of_week"] >= 5
    ).astype(int)

    # -----------------------------------------------------------------------
    # Remove columns that should not be used directly by the ML model
    # -----------------------------------------------------------------------

    columns_to_drop = [
        "transaction_id",
        "customer_id",
        "currency",
        "timestamp",
        "payment_method",
        "subscription_status",
        "failure_reason",
        "failure_category",
    ]

    features = features.drop(
        columns=columns_to_drop,
        errors="ignore",
    )

    return features


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_features(
    dataframe: pd.DataFrame,
) -> None:
    """Validate the generated ML feature dataset."""

    if dataframe.empty:
        raise ValueError(
            "Feature dataset is empty."
        )

    if dataframe.isnull().any().any():
        null_columns = dataframe.columns[
            dataframe.isnull().any()
        ].tolist()

        raise ValueError(
            f"Null values found in features: "
            f"{null_columns}"
        )

    if "recovered" not in dataframe.columns:
        raise ValueError(
            "Target column 'recovered' is missing."
        )

    if not dataframe["recovered"].isin(
        [0, 1]
    ).all():
        raise ValueError(
            "Target column 'recovered' must contain "
            "only 0 or 1."
        )

    print("Feature validation passed.")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the complete feature engineering pipeline."""

    print("Loading payment dataset...")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    dataframe = pd.read_csv(INPUT_FILE)

    print(
        f"Loaded {len(dataframe):,} transactions."
    )

    # We train the recovery model only on failed payments.
    failed_payments = dataframe[
        dataframe["status"] == "FAILED"
    ].copy()

    print(
        f"Failed payments available for recovery modeling: "
        f"{len(failed_payments):,}"
    )

    features = create_features(
        failed_payments
    )

    validate_features(features)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    features.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"Feature dataset saved to: {OUTPUT_FILE}"
    )

    print(
        f"Feature count: {len(features.columns)}"
    )


if __name__ == "__main__":
    main()
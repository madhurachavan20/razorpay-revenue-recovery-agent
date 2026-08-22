"""
Revenue recovery recommendation engine.

Uses the trained ML model to estimate recovery probability
and recommends the most appropriate recovery action.
"""

from pathlib import Path

import joblib
import pandas as pd


MODEL_FILE = Path(
    "ml/models/recovery_model.joblib"
)


# ---------------------------------------------------------------------------
# Recovery actions
# ---------------------------------------------------------------------------

RECOVERY_ACTIONS = {
    "TIMEOUT": "Retry payment",
    "NETWORK_ERROR": "Retry payment",
    "BANK_DECLINE": "Retry with another payment method",
    "INSUFFICIENT_FUNDS": "Notify customer to add funds",
    "AUTHENTICATION_FAILURE": "Request customer authentication",
    "CARD_DECLINE": "Ask customer to use another card",
    "EXPIRED_PAYMENT_METHOD": "Request payment method update",
}


# ---------------------------------------------------------------------------
# Priority calculation
# ---------------------------------------------------------------------------

def calculate_priority(
    probability: float,
    amount: float,
) -> str:
    """
    Determine recovery priority using probability and
    transaction value.
    """

    expected_recovery = probability * amount

    if expected_recovery >= 3000:
        return "HIGH"

    if expected_recovery >= 1000:
        return "MEDIUM"

    return "LOW"


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

def generate_recommendation(
    transaction: pd.Series,
    probability: float,
) -> dict:
    """Generate a business recommendation for one failed payment."""

    amount = float(
        transaction["amount"]
    )

    failure_reason = transaction[
        "failure_reason"
    ]

    expected_recovery = (
        probability * amount
    )

    priority = calculate_priority(
        probability,
        amount,
    )

    action = RECOVERY_ACTIONS.get(
        failure_reason,
        "Retry payment",
    )

    return {
        "transaction_id": transaction[
            "transaction_id"
        ],
        "customer_id": transaction[
            "customer_id"
        ],
        "amount": round(amount, 2),
        "failure_reason": failure_reason,
        "recovery_probability": round(
            probability,
            4,
        ),
        "priority": priority,
        "recommended_action": action,
        "expected_recovery_value": round(
            expected_recovery,
            2,
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate recovery recommendations for failed payments."""

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    input_file = Path(
        "data/payments.csv"
    )

    if not input_file.exists():
        raise FileNotFoundError(
            f"Payment dataset not found: {input_file}"
        )

    print("Loading recovery model...")

    model = joblib.load(
        MODEL_FILE
    )

    dataframe = pd.read_csv(
        input_file
    )

    failed_payments = dataframe[
        dataframe["status"] == "FAILED"
    ].copy()

    print(
        f"Generating recommendations for "
        f"{len(failed_payments):,} failed payments..."
    )

    # Recreate the same feature transformations used
    # during training.
    from ml.feature_engineering import (
        create_features,
    )

    model_features = create_features(
        failed_payments
    )

    # Remove target and leakage columns.
    model_features = model_features.drop(
        columns=[
            "recovered",
            "recovery_probability",
        ],
        errors="ignore",
    )

    probabilities = model.predict_proba(
        model_features
    )[:, 1]

    recommendations = []

    for index, probability in zip(
        failed_payments.index,
        probabilities,
    ):
        transaction = failed_payments.loc[
            index
        ]

        recommendation = generate_recommendation(
            transaction,
            float(probability),
        )

        recommendations.append(
            recommendation
        )

    recommendations_df = pd.DataFrame(
        recommendations
    )

    output_dir = Path(
        "data"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / "recovery_recommendations.csv"
    )

    recommendations_df.to_csv(
        output_file,
        index=False,
    )

    print(
        f"\nRecommendations saved to: "
        f"{output_file}"
    )

    print("\nPriority distribution")

    print(
        recommendations_df[
            "priority"
        ].value_counts().to_string()
    )

    print(
        "\nTotal expected recovery: "
        f"₹{recommendations_df['expected_recovery_value'].sum():,.2f}"
    )

    print("\nTop recovery opportunities")

    print(
        recommendations_df.sort_values(
            "expected_recovery_value",
            ascending=False,
        )
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
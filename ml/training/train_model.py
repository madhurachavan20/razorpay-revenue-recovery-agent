"""
Train the revenue recovery prediction model.

Input:
    ml/dataset/recovery_features.csv

Output:
    ml/models/recovery_model.joblib
"""

from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_FILE = Path(
    "ml/dataset/recovery_features.csv"
)

MODEL_DIR = Path("ml/models")

MODEL_FILE = (
    MODEL_DIR / "recovery_model.joblib"
)

TARGET_COLUMN = "recovered"


# ---------------------------------------------------------------------------
# Load dataset
# ---------------------------------------------------------------------------

def load_dataset() -> pd.DataFrame:
    """Load the engineered recovery dataset."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Feature dataset not found: {INPUT_FILE}"
        )

    dataframe = pd.read_csv(INPUT_FILE)

    if dataframe.empty:
        raise ValueError(
            "Training dataset is empty."
        )

    return dataframe


# ---------------------------------------------------------------------------
# Prepare training data
# ---------------------------------------------------------------------------

def prepare_data(
    dataframe: pd.DataFrame,
):
    """
    Separate features and target.

    The model predicts recovery for failed payments only.

    recovery_probability is excluded because it was generated
    using the synthetic recovery rules and would cause target
    leakage.

    status is also excluded because every training record is
    already a FAILED payment.
    """

    if TARGET_COLUMN not in dataframe.columns:
        raise ValueError(
            f"Target column '{TARGET_COLUMN}' "
            "is missing."
        )

    columns_to_exclude = [
        TARGET_COLUMN,
        "recovery_probability",
        "status",
    ]

    features = dataframe.drop(
        columns=columns_to_exclude,
        errors="ignore",
    )

    target = dataframe[TARGET_COLUMN]

    if not target.isin([0, 1]).all():
        raise ValueError(
            "Target must contain only 0 and 1."
        )

    return features, target

# ---------------------------------------------------------------------------
# Build model
# ---------------------------------------------------------------------------

def build_model(
    features: pd.DataFrame,
) -> Pipeline:
    """Build the preprocessing and classification pipeline."""

    numeric_features = features.select_dtypes(
        include=["number"]
    ).columns.tolist()

    categorical_features = features.select_dtypes(
        include=["object", "category","string"]
    ).columns.tolist()

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                numeric_features,
            ),
            (
                "categorical",
                categorical_pipeline,
                categorical_features,
            ),
        ],
        remainder="drop",
    )

    classifier = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )

    model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "classifier",
                classifier,
            ),
        ]
    )

    return model


# ---------------------------------------------------------------------------
# Train and evaluate
# ---------------------------------------------------------------------------

def train_model(
    features: pd.DataFrame,
    target: pd.Series,
) -> Pipeline:
    """Train and evaluate the recovery model."""

    X_train, X_test, y_train, y_test = (
        train_test_split(
            features,
            target,
            test_size=0.20,
            random_state=42,
            stratify=target,
        )
    )

    print(
        f"Training samples : {len(X_train):,}"
    )

    print(
        f"Testing samples  : {len(X_test):,}"
    )

    model = build_model(features)

    print("\nTraining model...")

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    roc_auc = roc_auc_score(
        y_test,
        probabilities,
    )

    print("\nModel Evaluation")
    print("-" * 40)

    print(
        f"Accuracy : {accuracy:.4f}"
    )

    print(
        f"ROC-AUC  : {roc_auc:.4f}"
    )

    print("\nClassification Report")

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "Not Recovered",
                "Recovered",
            ],
        )
    )

    print("Confusion Matrix")

    print(
        confusion_matrix(
            y_test,
            predictions,
        )
    )

    return model


# ---------------------------------------------------------------------------
# Save model
# ---------------------------------------------------------------------------

def save_model(
    model: Pipeline,
) -> None:
    """Save the trained model to disk."""

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_FILE,
    )

    print(
        f"\nModel saved to: {MODEL_FILE}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the complete model training pipeline."""

    print(
        "Loading feature dataset..."
    )

    dataframe = load_dataset()

    print(
        f"Loaded {len(dataframe):,} "
        "training records."
    )

    features, target = prepare_data(
        dataframe
    )

    print(
        f"Features used for training: "
        f"{len(features.columns)}"
    )

    print(
        f"Target distribution:\n"
        f"{target.value_counts().to_string()}"
    )

    model = train_model(
        features,
        target,
    )

    save_model(model)


if __name__ == "__main__":
    main()
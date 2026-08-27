"""
FastAPI backend for the Revenue Recovery Agent.
"""

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_FILE = Path(
    "data/recovery_recommendations.csv"
)

PAYMENTS_FILE = Path(
    "data/payments.csv"
)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Revenue Recovery Agent API",
    description=(
        "AI-powered API for identifying and prioritizing "
        "failed payment recovery opportunities."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_recommendations() -> pd.DataFrame:
    """Load recovery recommendations."""

    if not DATA_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Recovery recommendations not found.",
        )

    return pd.read_csv(DATA_FILE)


def load_payments() -> pd.DataFrame:
    """Load payment transactions."""

    if not PAYMENTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Payment dataset not found.",
        )

    return pd.read_csv(PAYMENTS_FILE)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Check whether the API is running."""

    return {
        "status": "healthy",
        "service": "revenue-recovery-agent",
    }


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------

@app.get("/metrics")
def get_metrics():
    """Return high-level revenue recovery metrics."""

    recommendations = load_recommendations()

    total_failed_payments = len(
        recommendations
    )

    total_expected_recovery = float(
        recommendations[
            "expected_recovery_value"
        ].sum()
    )

    high_priority = int(
        (
            recommendations["priority"]
            == "HIGH"
        ).sum()
    )

    medium_priority = int(
        (
            recommendations["priority"]
            == "MEDIUM"
        ).sum()
    )

    low_priority = int(
        (
            recommendations["priority"]
            == "LOW"
        ).sum()
    )

    return {
        "total_failed_payments": total_failed_payments,
        "total_expected_recovery": round(
            total_expected_recovery,
            2,
        ),
        "priority_distribution": {
            "HIGH": high_priority,
            "MEDIUM": medium_priority,
            "LOW": low_priority,
        },
    }


# ---------------------------------------------------------------------------
# Recovery opportunities
# ---------------------------------------------------------------------------

@app.get("/recovery-opportunities")
def get_recovery_opportunities(
    priority: str | None = None,
    limit: int = 50,
):
    """
    Return recovery opportunities.

    Optional priority filter:
        HIGH
        MEDIUM
        LOW
    """

    recommendations = load_recommendations()

    if priority:
        priority = priority.upper()

        if priority not in {
            "HIGH",
            "MEDIUM",
            "LOW",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Priority must be HIGH, "
                    "MEDIUM, or LOW."
                ),
            )

        recommendations = recommendations[
            recommendations["priority"]
            == priority
        ]

    limit = max(
        1,
        min(limit, 500),
    )

    recommendations = (
        recommendations
        .sort_values(
            "expected_recovery_value",
            ascending=False,
        )
        .head(limit)
    )

    return recommendations.to_dict(
        orient="records"
    )


# ---------------------------------------------------------------------------
# Single recovery opportunity
# ---------------------------------------------------------------------------

@app.get(
    "/recovery-opportunities/{transaction_id}"
)
def get_recovery_opportunity(
    transaction_id: str,
):
    """Return one recovery opportunity."""

    recommendations = load_recommendations()

    result = recommendations[
        recommendations["transaction_id"]
        == transaction_id
    ]

    if result.empty:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    return result.iloc[0].to_dict()


# ---------------------------------------------------------------------------
# Payment statistics
# ---------------------------------------------------------------------------

@app.get("/payments/summary")
def get_payment_summary():
    """Return summary statistics for all payments."""

    payments = load_payments()

    total_transactions = len(
        payments
    )

    successful = int(
        (
            payments["status"]
            == "SUCCESS"
        ).sum()
    )

    failed = int(
        (
            payments["status"]
            == "FAILED"
        ).sum()
    )

    total_value = float(
        payments["amount"].sum()
    )

    return {
        "total_transactions": total_transactions,
        "successful_payments": successful,
        "failed_payments": failed,
        "success_rate": round(
            successful / total_transactions,
            4,
        ),
        "failure_rate": round(
            failed / total_transactions,
            4,
        ),
        "total_transaction_value": round(
            total_value,
            2,
        ),
    }
from typing import Optional

from datetime import datetime, timedelta, timezone

import pandas as pd
import jwt

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Depends,
)

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

from pwdlib import PasswordHash

from backend.db_queries import (
    fetch_all,
    fetch_one,
    execute_query,
)


# ============================================================
# RevenueOS FastAPI Application
# PostgreSQL-backed version
# ============================================================

app = FastAPI(
    title="RevenueOS - Revenue Recovery Agent",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://razorpay-revenue-recovery-agent.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Authentication
# ============================================================

SECRET_KEY = "revenueos-buildathon-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

password_hash = PasswordHash.recommended()
security = HTTPBearer()


def create_access_token(user_id, email, role):

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return payload

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Session expired. Please login again.",
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
        )


# ============================================================
# Helper functions
# ============================================================

def safe_records(df):

    """
    Convert DataFrame values safely to JSON-compatible records.
    """

    return df.where(
        pd.notna(df),
        ""
    ).to_dict(
        orient="records"
    )


def priorities(df):

    """
    Return HIGH/MEDIUM/LOW priority counts.
    """

    out = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }

    if "priority" in df.columns:

        vc = (
            df["priority"]
            .astype(str)
            .str.upper()
            .value_counts()
        )

        for key in out:

            out[key] = int(
                vc.get(
                    key,
                    0
                )
            )

    return out


def breakdown(df, group):

    """
    Create analytics breakdowns.

    Returns:
        failed_payments
        revenue_at_risk
        expected_recovery
    """

    if group not in df.columns:

        return []

    aggregations = {
        "failed_payments": (
            "transaction_id",
            "count",
        ),

        "revenue_at_risk": (
            "amount",
            "sum",
        ),

        "expected_recovery": (
            "expected_recovery_value",
            "sum",
        ),
    }

    valid_aggs = {}

    for output_name, (
        source_column,
        operation,
    ) in aggregations.items():

        if source_column in df.columns:

            valid_aggs[output_name] = (
                source_column,
                operation,
            )

    if not valid_aggs:

        return []

    result = (
        df.groupby(
            group,
            dropna=False
        )
        .agg(
            **valid_aggs
        )
        .reset_index()
    )

    if "failed_payments" in result.columns:

        result = result.sort_values(
            "failed_payments",
            ascending=False,
        )

    return safe_records(
        result.round(2)
    )


# ============================================================
# PostgreSQL Recovery Loader
# ============================================================

def recs():

    """
    Load only PENDING recovery opportunities.

    EXECUTED opportunities are excluded from the
    active recovery queue.
    """

    query = """

        SELECT
            transaction_id,
            customer_id,
            payment_method,
            failure_category,
            amount,
            failure_reason,
            recovery_probability,
            priority,
            recommended_action,
            expected_recovery_value,
            recovery_status,
            created_at,
            updated_at

        FROM recovery_opportunities

        WHERE UPPER(recovery_status) = 'PENDING'

        ORDER BY expected_recovery_value DESC

    """

    rows = fetch_all(query)

    df = pd.DataFrame(rows)

    if df.empty:

        return pd.DataFrame(
            columns=[
                "transaction_id",
                "customer_id",
                "payment_method",
                "failure_category",
                "amount",
                "failure_reason",
                "recovery_probability",
                "priority",
                "recommended_action",
                "expected_recovery_value",
                "recovery_status",
                "created_at",
                "updated_at",
            ]
        )

    for column in [
        "amount",
        "expected_recovery_value",
        "recovery_probability",
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    for column in [
        "transaction_id",
        "customer_id",
        "payment_method",
        "failure_reason",
        "failure_category",
        "priority",
        "recommended_action",
        "recovery_status",
    ]:

        if column in df.columns:

            df[column] = (
                df[column]
                .fillna("UNKNOWN")
                .astype(str)
                .str.strip()
            )

    for column in [
        "payment_method",
        "failure_reason",
        "failure_category",
        "priority",
        "recovery_status",
    ]:

        if column in df.columns:

            df[column] = (
                df[column]
                .str.upper()
            )

    return df


# ============================================================
# PostgreSQL Payments Loader
# ============================================================

def pays():

    """
    Load payments from PostgreSQL.
    """

    query = """

        SELECT
            transaction_id,
            customer_id,
            payment_method,
            amount,
            status,
            failure_reason,
            failure_category,
            created_at

        FROM payments

        ORDER BY created_at DESC

    """

    rows = fetch_all(query)

    df = pd.DataFrame(rows)

    if df.empty:

        return pd.DataFrame(
            columns=[
                "transaction_id",
                "customer_id",
                "payment_method",
                "amount",
                "status",
                "failure_reason",
                "failure_category",
                "created_at",
            ]
        )

    if "amount" in df.columns:

        df["amount"] = pd.to_numeric(
            df["amount"],
            errors="coerce",
        ).fillna(0)

    for column in [
        "transaction_id",
        "customer_id",
        "status",
        "payment_method",
        "failure_reason",
        "failure_category",
    ]:

        if column in df.columns:

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    for column in [
        "status",
        "payment_method",
        "failure_reason",
        "failure_category",
    ]:

        if column in df.columns:

            df[column] = (
                df[column]
                .str.upper()
            )

    return df


# ============================================================
# Basic Endpoints
# ============================================================

@app.get("/")
def root():

    return {
        "service": "RevenueOS",
        "status": "online",
        "database": "PostgreSQL",
        "dashboard": "/dashboard/summary",
        "docs": "/docs",
    }


@app.get("/health")
def health():

    try:

        result = fetch_one(
            "SELECT 1 AS database_status"
        )

        if (
            result
            and result["database_status"] == 1
        ):

            return {
                "status": "healthy",
                "service": "RevenueOS",
                "database": "connected",
            }

        raise Exception(
            "Database check failed"
        )

    except Exception as e:

        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {e}",
        )


# ============================================================
# Authentication - Login
# ============================================================

@app.post("/auth/login")
def login(credentials: dict):

    email = str(
        credentials.get(
            "email",
            ""
        )
    ).strip().lower()

    password = str(
        credentials.get(
            "password",
            ""
        )
    )

    if not email or not password:

        raise HTTPException(
            status_code=400,
            detail="Email and password are required.",
        )

    user = fetch_one(
        """

        SELECT
            id,
            email,
            password_hash,
            name,
            role

        FROM users

        WHERE LOWER(email) = LOWER(%s)

        """,
        (email,),
    )

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    try:

        valid_password = password_hash.verify(
            password,
            user["password_hash"],
        )

    except Exception:

        valid_password = False

    if not valid_password:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    token = create_access_token(
        user["id"],
        user["email"],
        user["role"],
    )

    return {

        "success": True,

        "access_token": token,

        "token_type": "bearer",

        "user": {

            "id": user["id"],

            "email": user["email"],

            "name": user["name"],

            "role": user["role"],
        },
    }


# ============================================================
# Dashboard
# ============================================================

@app.get("/dashboard/summary")
def dashboard_summary():

    p = pays()

    # Load ALL recovery opportunities
    # for dashboard analytics.

    all_recovery_rows = fetch_all(
        """

        SELECT
            transaction_id,
            customer_id,
            payment_method,
            failure_category,
            amount,
            failure_reason,
            recovery_probability,
            priority,
            recommended_action,
            expected_recovery_value,
            recovery_status,
            created_at,
            updated_at

        FROM recovery_opportunities

        ORDER BY expected_recovery_value DESC

        """
    )

    r = pd.DataFrame(
        all_recovery_rows
    )

    total = len(p)

    success = (
        int(
            (
                p["status"] == "SUCCESS"
            ).sum()
        )
        if "status" in p.columns
        else 0
    )

    failed = (
        int(
            (
                p["status"] == "FAILED"
            ).sum()
        )
        if "status" in p.columns
        else len(r)
    )

    risk = (
        float(
            r["amount"].sum()
        )
        if "amount" in r.columns
        else 0
    )

    expected = (
        float(
            r[
                "expected_recovery_value"
            ].sum()
        )
        if "expected_recovery_value"
        in r.columns
        else 0
    )

    if "expected_recovery_value" in r.columns:

        top = (
            r.sort_values(
                "expected_recovery_value",
                ascending=False,
            )
            .head(10)
        )

    else:

        top = r.head(10)

    methods = breakdown(
        r,
        "payment_method",
    )

    failures = breakdown(
        r,
        "failure_category",
    )

    reasons = []

    if "failure_reason" in r.columns:

        x = (
            r.groupby(
                "failure_reason"
            )
            .agg(
                failed_payments=(
                    "transaction_id",
                    "count",
                )
            )
            .reset_index()
            .sort_values(
                "failed_payments",
                ascending=False,
            )
        )

        reasons = safe_records(x)

    return {

        "status": "success",

        "payment_metrics": {

            "total_transactions": total,

            "successful_payments": success,

            "failed_payments": failed,

            "success_rate": (
                success / total
                if total
                else 0
            ),

            "failure_rate": (
                failed / total
                if total
                else 0
            ),

            "total_transaction_value": (

                float(
                    p["amount"].sum()
                )

                if "amount" in p.columns

                else 0
            ),
        },

        "recovery_metrics": {

            "total_failed_payments": len(r),

            "revenue_at_risk": risk,

            "expected_recovery": expected,

            "recovery_rate": (

                expected / risk

                if risk

                else 0
            ),

            "average_recovery_probability": (

                float(
                    r[
                        "recovery_probability"
                    ].mean()
                )

                if "recovery_probability"
                in r.columns

                else 0
            ),
        },

        "priority_distribution": priorities(r),

        "payment_method_breakdown": methods,

        "failure_category_breakdown": failures,

        "failure_reason_breakdown": reasons,

        "top_opportunities": safe_records(
            top
        ),
    }


# ============================================================
# Metrics
# ============================================================

@app.get("/metrics")
def metrics():

    d = dashboard_summary()

    return {

        "total_failed_payments": d[
            "recovery_metrics"
        ][
            "total_failed_payments"
        ],

        "total_expected_recovery": d[
            "recovery_metrics"
        ][
            "expected_recovery"
        ],

        "priority_distribution": d[
            "priority_distribution"
        ],
    }


# ============================================================
# Recovery Opportunities
# ============================================================

@app.get("/recovery-opportunities")
def recovery_opportunities(

    priority: str = "",

    limit: int = 100,

    search: str = "",

    status: str = "",
):

    query = """

        SELECT
            transaction_id,
            customer_id,
            payment_method,
            failure_category,
            amount,
            failure_reason,
            recovery_probability,
            priority,
            recommended_action,
            expected_recovery_value,
            recovery_status,
            created_at,
            updated_at

        FROM recovery_opportunities

        WHERE 1 = 1

    """

    params = []

    if priority:

        query += """

            AND UPPER(priority)
            = UPPER(%s)

        """

        params.append(
            priority
        )

    if status:

        query += """

            AND UPPER(recovery_status)
            = UPPER(%s)

        """

        params.append(
            status
        )

    if search:

        query += """

            AND (
                transaction_id ILIKE %s
                OR customer_id ILIKE %s
            )

        """

        search_value = (
            f"%{search}%"
        )

        params.extend(
            [
                search_value,
                search_value,
            ]
        )

    query += """

        ORDER BY expected_recovery_value DESC

        LIMIT %s

    """

    params.append(limit)

    try:

        return fetch_all(
            query,
            tuple(params),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to fetch recovery "
                f"opportunities: {str(e)}"
            ),
        )


# ============================================================
# Payments
# ============================================================

@app.get("/payments/summary")
def payment_summary():

    p = pays()

    total = len(p)

    success = (
        int(
            (
                p["status"] == "SUCCESS"
            ).sum()
        )
        if "status" in p.columns
        else 0
    )

    failed = (
        int(
            (
                p["status"] == "FAILED"
            ).sum()
        )
        if "status" in p.columns
        else 0
    )

    return {

        "total_transactions": total,

        "successful_payments": success,

        "failed_payments": failed,

        "success_rate": (
            success / total
            if total
            else 0
        ),

        "failure_rate": (
            failed / total
            if total
            else 0
        ),

        "total_transaction_value": (

            float(
                p["amount"].sum()
            )

            if "amount" in p.columns

            else 0
        ),
    }


@app.get("/payments")
def payments(

    status: Optional[str] = Query(
        None
    ),

    limit: int = Query(
        100,
        ge=1,
        le=1000,
    ),
):

    df = pays()

    if status:

        st = status.strip().upper()

        if st not in {
            "SUCCESS",
            "FAILED",
        }:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Status must be "
                    "SUCCESS or FAILED."
                ),
            )

        df = df[
            df["status"] == st
        ]

    return {

        "status": "success",

        "count": min(
            len(df),
            limit,
        ),

        "data": safe_records(
            df.head(limit)
        ),
    }


# ============================================================
# Customers
# ============================================================

@app.get("/customers")
def customers(

    limit: int = Query(
        100,
        ge=1,
        le=1000,
    ),

):

    query = """

        SELECT
            c.customer_id,

            COUNT(
                r.transaction_id
            ) AS failed_payments,

            COALESCE(
                SUM(r.amount),
                0
            ) AS revenue_at_risk,

            COALESCE(
                SUM(
                    r.expected_recovery_value
                ),
                0
            ) AS expected_recovery,

            COALESCE(
                AVG(
                    r.recovery_probability
                ),
                0
            ) AS average_recovery_probability

        FROM customers c

        LEFT JOIN recovery_opportunities r
            ON c.customer_id =
               r.customer_id

        GROUP BY c.customer_id

        HAVING COUNT(
            r.transaction_id
        ) > 0

        ORDER BY expected_recovery DESC

        LIMIT %s

    """

    rows = fetch_all(
        query,
        (limit,),
    )

    return {

        "status": "success",

        "count": len(rows),

        "data": rows,
    }


# ============================================================
# Analytics
# ============================================================

@app.get("/analytics/overview")
def analytics_overview():

    d = dashboard_summary()

    return {

        **d[
            "payment_metrics"
        ],

        "revenue_at_risk": d[
            "recovery_metrics"
        ][
            "revenue_at_risk"
        ],

        "expected_recovery": d[
            "recovery_metrics"
        ][
            "expected_recovery"
        ],

        "recovery_rate": d[
            "recovery_metrics"
        ][
            "recovery_rate"
        ],
    }


@app.get("/analytics/payment-methods")
def analytics_methods():

    return dashboard_summary()[
        "payment_method_breakdown"
    ]


@app.get("/analytics/failure-categories")
def analytics_failures():

    return dashboard_summary()[
        "failure_category_breakdown"
    ]


@app.get("/analytics/recovery-priorities")
def analytics_priorities():

    d = dashboard_summary()

    return [

        {
            "priority": key,
            "opportunities": value,
        }

        for key, value
        in d[
            "priority_distribution"
        ].items()

    ]


# ============================================================
# Recovery Action Center
# ============================================================

RECOVERY_ACTIONS = {

    "RETRY_PAYMENT":
        "Retry payment",

    "CHANGE_PAYMENT_METHOD":
        "Retry with another payment method",

    "ADD_FUNDS":
        "Notify customer to add funds",

    "CONTACT_CUSTOMER":
        "Contact customer",
}


# ============================================================
# Execute Recovery
# ============================================================

@app.post(
    "/recovery/{transaction_id}/execute"
)
def execute_recovery(
    transaction_id: str,
):

    transaction_id = (
        transaction_id.strip()
    )

    # --------------------------------------------------------
    # Get recovery opportunity
    # --------------------------------------------------------

    row = fetch_one(
        """

        SELECT
            transaction_id,
            customer_id,
            payment_method,
            failure_category,
            failure_reason,
            amount,
            recovery_probability,
            priority,
            recommended_action,
            expected_recovery_value,
            recovery_status

        FROM recovery_opportunities

        WHERE transaction_id = %s

        """,
        (transaction_id,),
    )

    if row is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Recovery opportunity not found: "
                f"{transaction_id}"
            ),
        )

    customer_id = str(
        row.get(
            "customer_id",
            "",
        )
    )

    action = str(
        row.get(
            "recommended_action",
            "Retry payment",
        )
    )

    amount = float(
        row.get(
            "amount",
            0,
        )
        or 0
    )

    probability = float(
        row.get(
            "recovery_probability",
            0,
        )
        or 0
    )

    expected_recovery = float(
        row.get(
            "expected_recovery_value",
            0,
        )
        or 0
    )

    current_status = str(
        row.get(
            "recovery_status",
            "PENDING",
        )
    ).upper()

    # --------------------------------------------------------
    # Prevent duplicate execution while currently EXECUTED
    # --------------------------------------------------------

    if current_status == "EXECUTED":

        previous = fetch_one(
            """

            SELECT
                transaction_id,
                action,
                result,
                message,
                executed_at

            FROM recovery_executions

            WHERE transaction_id = %s

            ORDER BY executed_at DESC

            LIMIT 1

            """,
            (transaction_id,),
        )

        return {

            "success": True,

            "already_executed": True,

            "transaction_id":
                transaction_id,

            "customer_id":
                customer_id,

            "action":
                previous.get(
                    "action",
                    action,
                )
                if previous
                else action,

            "amount":
                amount,

            "recovery_probability":
                probability,

            "expected_recovery":
                expected_recovery,

            "status":
                "EXECUTED",

            "message":
                (
                    "Recovery action was already "
                    "executed for this transaction."
                ),
        }

    # --------------------------------------------------------
    # Execute new recovery action
    # --------------------------------------------------------

    result = "SUCCESS"

    message = (
        "Recovery action executed successfully: "
        f"{action}"
    )

    # --------------------------------------------------------
    # Record execution
    # --------------------------------------------------------

    execute_query(
        """

        INSERT INTO recovery_executions
        (
            transaction_id,
            action,
            result,
            message
        )

        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )

        """,
        (
            transaction_id,
            action,
            result,
            message,
        ),
    )

    # --------------------------------------------------------
    # Update recovery status
    # --------------------------------------------------------

    execute_query(
        """

        UPDATE recovery_opportunities

        SET
            recovery_status = 'EXECUTED',
            updated_at = CURRENT_TIMESTAMP

        WHERE transaction_id = %s

        """,
        (transaction_id,),
    )

    # --------------------------------------------------------
    # Get execution timestamp
    # --------------------------------------------------------

    executed = fetch_one(
        """

        SELECT executed_at

        FROM recovery_executions

        WHERE transaction_id = %s

        ORDER BY executed_at DESC

        LIMIT 1

        """,
        (transaction_id,),
    )

    executed_at = (
        executed.get(
            "executed_at"
        )
        if executed
        else None
    )

    return {

        "success": True,

        "already_executed": False,

        "transaction_id":
            transaction_id,

        "customer_id":
            customer_id,

        "action":
            action,

        "amount":
            amount,

        "recovery_probability":
            probability,

        "expected_recovery":
            expected_recovery,

        "status":
            "EXECUTED",

        "result":
            result,

        "executed_at":
            executed_at,

        "message":
            (
                "Recovery action executed and "
                "recorded successfully in PostgreSQL."
            ),
    }


# ============================================================
# Recovery History
# ============================================================

@app.get("/recovery-history")
def recovery_history():

    query = """

        SELECT
            e.transaction_id,

            p.customer_id,

            e.action,

            p.amount,

            r.recovery_probability,

            r.expected_recovery_value
                AS expected_recovery,

            COALESCE(
                e.result,
                'SUCCESS'
            ) AS result,

            COALESCE(
                e.message,
                'Recovery action executed successfully.'
            ) AS message,

            COALESCE(
                e.result,
                'SUCCESS'
            ) AS status,

            e.executed_at

        FROM recovery_executions e

        LEFT JOIN payments p
            ON e.transaction_id =
               p.transaction_id

        LEFT JOIN recovery_opportunities r
            ON e.transaction_id =
               r.transaction_id

        ORDER BY e.executed_at DESC

    """

    rows = fetch_all(query)

    return {

        "status": "success",

        "count": len(rows),

        "data": rows,
    }


# ============================================================
# Recovery Details
# ============================================================

@app.get(
    "/recovery/{transaction_id}/details"
)
def get_recovery_details(
    transaction_id: str,
):

    query = """

        SELECT
            transaction_id,
            customer_id,
            payment_method,
            failure_category,
            failure_reason,
            amount,
            recovery_probability,
            priority,
            recommended_action,
            expected_recovery_value,
            recovery_status

        FROM recovery_opportunities

        WHERE transaction_id = %s

    """

    transaction = fetch_one(
        query,
        (
            transaction_id.strip(),
        ),
    )

    if transaction is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Recovery opportunity "
                "not found."
            ),
        )

    probability = float(
        transaction.get(
            "recovery_probability",
            0,
        )
        or 0
    )

    amount = float(
        transaction.get(
            "amount",
            0,
        )
        or 0
    )

    expected_recovery = float(
        transaction.get(
            "expected_recovery_value",
            0,
        )
        or 0
    )

    return {

        "status":
            "success",

        "transaction_id":
            str(
                transaction.get(
                    "transaction_id",
                    "",
                )
            ),

        "customer_id":
            str(
                transaction.get(
                    "customer_id",
                    "",
                )
            ),

        "payment_method":
            str(
                transaction.get(
                    "payment_method",
                    "",
                )
            ),

        "failure_category":
            str(
                transaction.get(
                    "failure_category",
                    "",
                )
            ),

        "failure_reason":
            str(
                transaction.get(
                    "failure_reason",
                    "",
                )
            ),

        "amount":
            round(
                amount,
                2,
            ),

        "recovery_probability":
            round(
                probability,
                4,
            ),

        "priority":
            str(
                transaction.get(
                    "priority",
                    "",
                )
            ),

        "recommended_action":
            str(
                transaction.get(
                    "recommended_action",
                    "Retry payment",
                )
            ),

        "expected_recovery_value":
            round(
                expected_recovery,
                2,
            ),

        "recovery_status":
            str(
                transaction.get(
                    "recovery_status",
                    "PENDING",
                )
            ),
    }


# ============================================================
# Reset Recovery
# ============================================================

@app.post(
    "/recovery/{transaction_id}/reset"
)
def reset_recovery(
    transaction_id: str
):

    transaction_id = (
        transaction_id.strip()
    )

    # --------------------------------------------------------
    # Check opportunity exists
    # --------------------------------------------------------

    existing = fetch_one(
        """

        SELECT
            transaction_id,
            recovery_status

        FROM recovery_opportunities

        WHERE transaction_id = %s

        """,
        (transaction_id,),
    )

    if existing is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Recovery opportunity "
                f"not found: {transaction_id}"
            ),
        )

    # --------------------------------------------------------
    # Reset status to PENDING
    #
    # IMPORTANT:
    # Execution history is NOT deleted.
    # --------------------------------------------------------

    execute_query(
        """

        UPDATE recovery_opportunities

        SET
            recovery_status = 'PENDING',
            updated_at = CURRENT_TIMESTAMP

        WHERE transaction_id = %s

        """,
        (transaction_id,),
    )

    return {

        "success": True,

        "transaction_id":
            transaction_id,

        "previous_status":
            existing.get(
                "recovery_status"
            ),

        "status":
            "PENDING",

        "message":
            "Recovery opportunity reset to PENDING.",
    }
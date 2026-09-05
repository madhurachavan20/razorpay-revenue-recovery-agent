import pandas as pd
from db import get_connection


def migrate_customers(conn, payments_df):
    print("\n📦 Migrating customers...")

    customers = payments_df[
        [
            "customer_id",
            "customer_age_days",
            "previous_successful_payments",
            "previous_failed_payments",
            "customer_success_rate",
        ]
    ].drop_duplicates(subset=["customer_id"])

    cursor = conn.cursor()

    query = """
        INSERT INTO customers (
            customer_id,
            customer_age_days,
            previous_successful_payments,
            previous_failed_payments,
            customer_success_rate
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (customer_id) DO NOTHING;
    """

    count = 0

    for row in customers.itertuples(index=False):
        cursor.execute(query, tuple(row))
        count += 1

    conn.commit()
    cursor.close()

    print(f"✅ Customers processed: {count}")


def migrate_payments(conn, payments_df):
    print("\n💳 Migrating payments...")

    cursor = conn.cursor()

    query = """
        INSERT INTO payments (
            transaction_id,
            customer_id,
            payment_method,
            amount,
            status,
            failure_reason,
            failure_category,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (transaction_id) DO NOTHING;
    """

    count = 0

    for row in payments_df.itertuples(index=False):
        cursor.execute(
            query,
            (
                row.transaction_id,
                row.customer_id,
                row.payment_method,
                row.amount,
                row.status,
                row.failure_reason,
                row.failure_category,
                row.timestamp,
            ),
        )
        count += 1

    conn.commit()
    cursor.close()

    print(f"✅ Payments processed: {count}")


def migrate_recovery_opportunities(conn, recovery_df):
    print("\n🎯 Migrating recovery opportunities...")

    cursor = conn.cursor()

    query = """
        INSERT INTO recovery_opportunities (
            transaction_id,
            customer_id,
            amount,
            recovery_probability,
            expected_recovery_value,
            priority,
            recommended_action,
            failure_category,
            failure_reason,
            payment_method,
            recovery_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
    """

    count = 0

    for row in recovery_df.itertuples(index=False):
        cursor.execute(
            query,
            (
                row.transaction_id,
                row.customer_id,
                row.amount,
                row.recovery_probability,
                row.expected_recovery_value,
                row.priority,
                row.recommended_action,
                row.failure_category,
                row.failure_reason,
                row.payment_method,
                "PENDING",
            ),
        )
        count += 1

    conn.commit()
    cursor.close()

    print(f"✅ Recovery opportunities processed: {count}")


def migrate_recovery_history(conn, history_df):
    print("\n⚡ Migrating recovery history...")

    cursor = conn.cursor()

    query = """
        INSERT INTO recovery_executions (
            transaction_id,
            action,
            result,
            message,
            executed_at
        )
        VALUES (%s, %s, %s, %s, %s);
    """

    count = 0

    for row in history_df.itertuples(index=False):
        message = (
            f"Customer: {row.customer_id} | "
            f"Amount: {row.amount} | "
            f"Recovery probability: {row.recovery_probability} | "
            f"Expected recovery: {row.expected_recovery}"
        )

        cursor.execute(
            query,
            (
                row.transaction_id,
                row.action,
                row.status,
                message,
                row.executed_at,
            ),
        )

        count += 1

    conn.commit()
    cursor.close()

    print(f"✅ Recovery executions processed: {count}")


def main():
    print("🚀 Starting RevenueOS PostgreSQL migration...\n")

    print("📖 Reading CSV files...")

    payments_df = pd.read_csv("data/payments.csv")
    recovery_df = pd.read_csv("data/recovery_recommendations.csv")
    history_df = pd.read_csv("data/recovery_history.csv")

    print(f"Payments CSV: {len(payments_df):,} rows")
    print(f"Recovery recommendations: {len(recovery_df):,} rows")
    print(f"Recovery history: {len(history_df):,} rows")

    conn = get_connection()

    try:
        migrate_customers(conn, payments_df)
        migrate_payments(conn, payments_df)
        migrate_recovery_opportunities(conn, recovery_df)
        migrate_recovery_history(conn, history_df)

        print("\n" + "=" * 50)
        print("🎉 PostgreSQL migration completed successfully!")
        print("=" * 50)

    except Exception as e:
        conn.rollback()
        print("\n❌ Migration failed!")
        print("Error:", e)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
from db import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT
        table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position;
    """

    cursor.execute(query)

    rows = cursor.fetchall()

    print("✅ PostgreSQL connected!")
    print("\nTable columns:\n")

    for table, column, data_type in rows:
        print(f"{table} -> {column} ({data_type})")

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ Error:")
    print(e)
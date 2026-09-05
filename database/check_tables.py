from db import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)

    tables = cursor.fetchall()

    print("✅ PostgreSQL connected!")
    print("\nTables in revenueos database:")

    for table in tables:
        print(" -", table[0])

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ Error:")
    print(e)
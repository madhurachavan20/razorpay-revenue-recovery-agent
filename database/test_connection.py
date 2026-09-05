from db import get_connection

try:
    conn = get_connection()
    print("✅ PostgreSQL connection successful!")

    cursor = conn.cursor()
    cursor.execute("SELECT current_database();")

    result = cursor.fetchone()
    print("Connected database:", result[0])

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ PostgreSQL connection failed:")
    print(e)
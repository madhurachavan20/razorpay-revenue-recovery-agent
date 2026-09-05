from database.db import get_connection

connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
    SELECT transaction_id, recovery_status
    FROM recovery_opportunities
    WHERE transaction_id = 'TXN_0002896'
""")

print(cursor.fetchone())

cursor.close()
connection.close()
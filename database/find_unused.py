from database.db import get_connection

connection = get_connection()
cursor = connection.cursor()

query = """
SELECT r.transaction_id
FROM recovery_opportunities r
LEFT JOIN recovery_executions e
    ON r.transaction_id = e.transaction_id
WHERE e.transaction_id IS NULL
LIMIT 1
"""

cursor.execute(query)

result = cursor.fetchone()

if result:
    print("Unused transaction:", result[0])
else:
    print("No unused recovery opportunity found.")

cursor.close()
connection.close()
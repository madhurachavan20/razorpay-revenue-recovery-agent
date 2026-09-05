from database.db import get_connection


def fetch_all(query, params=None):
    """Execute a SELECT query and return rows as dictionaries."""
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(query, params or ())

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    finally:
        cursor.close()
        connection.close()


def fetch_one(query, params=None):
    """Execute a SELECT query and return one row as a dictionary."""
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(query, params or ())

        row = cursor.fetchone()

        if row is None:
            return None

        columns = [desc[0] for desc in cursor.description]

        return dict(zip(columns, row))

    finally:
        cursor.close()
        connection.close()


def execute_query(query, params=None):
    """Execute INSERT/UPDATE/DELETE query."""
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(query, params or ())

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()